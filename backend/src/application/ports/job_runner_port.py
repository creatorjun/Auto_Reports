# backend/src/application/ports/job_runner_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.job import JobRecord


class JobRunnerPort(ABC):
    @property
    @abstractmethod
    def is_running(self) -> bool: ...

    @abstractmethod
    def current_job_id(self) -> str | None: ...

    @abstractmethod
    async def execute_in_background(
        self,
        job_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobRecord | None: ...

    @abstractmethod
    async def run_scheduled_job(self) -> None: ...
