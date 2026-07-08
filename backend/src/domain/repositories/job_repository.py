# backend/src/domain/repositories/job_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.job import JobRecord


class JobRepository(ABC):
    @abstractmethod
    async def save(self, record: JobRecord) -> None: ...

    @abstractmethod
    async def find(self, job_id: str) -> Optional[JobRecord]: ...
