# backend/src/application/ports/job_runner_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.job import JobRecord, JobStatus


class JobRunnerPort(ABC):
    @abstractmethod
    async def submit(
        self,
        job_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobRecord | None: ...

    @abstractmethod
    async def wait_for_update(
        self,
        job_id: str,
        known_status: JobStatus,
        timeout: float = 30.0,
    ) -> None: ...

    @abstractmethod
    async def run_scheduled_job(self) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...
