# backend/src/infrastructure/persistence/job_repository_impl.py
from typing import Optional

from src.domain.entities.job import JobRecord
from src.domain.repositories.job_repository import JobRepository


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._store: dict[str, JobRecord] = {}

    async def save(self, record: JobRecord) -> None:
        self._store[record.job_id] = record

    async def find(self, job_id: str) -> Optional[JobRecord]:
        return self._store.get(job_id)
