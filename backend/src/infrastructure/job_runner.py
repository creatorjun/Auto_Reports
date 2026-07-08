# backend/src/infrastructure/job_runner.py
import logging
import uuid

from src.infrastructure.container import Container
from src.infrastructure.persistence.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, container: Container):
        self._container = container
        self._jobs: dict[str, dict] = {}

    def get_job_status(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    async def execute_in_background(self, job_id: str) -> None:
        self._jobs[job_id] = {"status": "running", "report_id": None, "error": None}
        try:
            async with AsyncSessionLocal() as session:
                uc = self._container.generate_report_use_case(session)
                report = await uc.execute()
            self._jobs[job_id] = {"status": "done", "report_id": report.id, "error": None}
            logger.info(f"[job:{job_id}] 완료 report_id={report.id}")
        except Exception as e:
            self._jobs[job_id] = {"status": "error", "report_id": None, "error": str(e)}
            logger.error(f"[job:{job_id}] 실패: {e}")

    async def run_scheduled_job(self) -> None:
        job_id = str(uuid.uuid4())
        logger.info(f"스케줄 실행 [job:{job_id}]")
        await self.execute_in_background(job_id)
