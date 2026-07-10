# backend/src/infrastructure/persistence/job_repository_impl.py
from typing import Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.entities.job import JobRecord, JobStatus
from src.domain.repositories.job_repository import JobRepository
from src.infrastructure.persistence.models import JobORM


class SqlJobRepository(JobRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, record: JobRecord) -> None:
        async with self._session_factory() as session:
            stmt = (
                insert(JobORM)
                .values(
                    job_id=record.job_id,
                    status=record.status,
                    report_id=record.report_id,
                    error=record.error,
                )
                .on_conflict_do_update(
                    index_elements=["job_id"],
                    set_={
                        "status": record.status,
                        "report_id": record.report_id,
                        "error": record.error,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def find(self, job_id: str) -> Optional[JobRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobORM).where(JobORM.job_id == job_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return JobRecord(
                job_id=row.job_id,
                status=JobStatus(row.status),
                report_id=row.report_id,
                error=row.error,
            )
