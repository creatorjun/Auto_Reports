# backend/src/infrastructure/job_runner.py
import asyncio
import logging
import uuid
from datetime import datetime

from src.application.ports.job_runner_port import JobRunnerPort
from src.domain.entities.job import JobRecord, JobStatus
from src.domain.repositories.job_repository import JobRepository
from src.infrastructure.container import Container
from src.infrastructure.persistence.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class JobRunner(JobRunnerPort):
    def __init__(self, container: Container, job_repository: JobRepository):
        self._container = container
        self._repo = job_repository
        self._lock = asyncio.Lock()
        self._running_job_id: str | None = None

    @property
    def is_running(self) -> bool:
        return self._running_job_id is not None

    def current_job_id(self) -> str | None:
        return self._running_job_id

    async def get_job_status(self, job_id: str) -> JobRecord | None:
        return await self._repo.find(job_id)

    async def execute_in_background(
        self,
        job_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        async with self._lock:
            if self._running_job_id is not None:
                logger.warning(
                    f"[job:{job_id}] 이미 실행 중인 job이 있어 건너뜁니다. "
                    f"running={self._running_job_id}"
                )
                await self._repo.save(
                    JobRecord(
                        job_id=job_id,
                        status=JobStatus.ERROR,
                        error=f"이미 실행 중인 보고서 생성 작업이 있습니다. (job_id={self._running_job_id})",
                    )
                )
                return
            self._running_job_id = job_id

        await self._repo.save(JobRecord(job_id=job_id, status=JobStatus.RUNNING))
        try:
            async with AsyncSessionLocal() as session:
                uc = self._container.generate_report_use_case(session)
                report = await uc.execute(start_date=start_date, end_date=end_date)
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.DONE, report_id=report.id)
            )
            logger.info(f"[job:{job_id}] 완료 report_id={report.id}")
        except Exception as e:
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.ERROR, error=str(e))
            )
            logger.error(f"[job:{job_id}] 실패: {e}")
        finally:
            async with self._lock:
                self._running_job_id = None

    async def run_scheduled_job(self) -> None:
        job_id = str(uuid.uuid4())
        logger.info(f"스케줄 실행 [job:{job_id}]")
        await self.execute_in_background(job_id)
