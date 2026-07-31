# backend/src/infrastructure/job_runner.py
import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ports.job_runner_port import JobRunnerPort
from src.domain.entities.job import JobRecord, JobStatus
from src.domain.repositories.job_repository import JobRepository
from src.infrastructure.container import Container

logger = logging.getLogger(__name__)


class JobRunner(JobRunnerPort):
    def __init__(
        self,
        container: Container,
        job_repository: JobRepository,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._container = container
        self._repo = job_repository
        self._session_factory = session_factory
        self._lock = asyncio.Lock()
        self._running_job_id: str | None = None
        self._notify_events: dict[str, asyncio.Event] = {}

    @property
    def is_running(self) -> bool:
        return self._running_job_id is not None

    def current_job_id(self) -> str | None:
        return self._running_job_id

    def _get_or_create_event(self, job_id: str) -> asyncio.Event:
        if job_id not in self._notify_events:
            self._notify_events[job_id] = asyncio.Event()
        return self._notify_events[job_id]

    def _notify(self, job_id: str) -> None:
        event = self._get_or_create_event(job_id)
        event.set()
        event.clear()

    async def wait_for_update(self, job_id: str, timeout: float = 30.0) -> None:
        event = self._get_or_create_event(job_id)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    async def save_pending(self, job_id: str) -> None:
        await self._repo.save(JobRecord(job_id=job_id, status=JobStatus.PENDING))
        self._notify(job_id)

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
                self._notify(job_id)
                return
            self._running_job_id = job_id

        await self._repo.save(JobRecord(job_id=job_id, status=JobStatus.RUNNING))
        self._notify(job_id)
        try:
            async with self._session_factory() as session:
                uc = self._container.generate_report_use_case(session)
                report = await uc.execute(start_date=start_date, end_date=end_date)
                await session.commit()
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.DONE, report_id=report.id)
            )
            self._notify(job_id)
            logger.info(f"[job:{job_id}] 완료 report_id={report.id}")
        except Exception as e:
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.ERROR, error=str(e))
            )
            self._notify(job_id)
            logger.error(f"[job:{job_id}] 실패: {e}")
        finally:
            async with self._lock:
                self._running_job_id = None
            self._notify_events.pop(job_id, None)

    async def run_scheduled_job(self) -> None:
        job_id = str(uuid.uuid4())
        logger.info(f"스케줄 실행 [job:{job_id}]")
        await self.execute_in_background(job_id)
