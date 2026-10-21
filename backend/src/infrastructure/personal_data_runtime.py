# backend/src/infrastructure/personal_data_runtime.py
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from sqlalchemy import text

from src.application.ports.personal_data_port import PersonalDataReportingLockPort, PersonalDataSnapshotPort
from src.domain.entities.personal_data import PersonalDataAccount
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore


class PersonalDataSnapshots(PersonalDataSnapshotPort):
    def __init__(self, database: Database, clear_caches: Callable[[], Awaitable[None]] | None = None) -> None:
        self._database = database
        self._clear_caches = clear_caches

    async def collect_accounts(self) -> tuple[PersonalDataAccount, ...]:
        async with self._database.session() as session:
            return await PersonalDataSnapshotStore(session).collect_accounts()

    async def erase_personal_data(self, account_ids: tuple[str, ...]) -> int:
        async with self._database.session() as session:
            count = await PersonalDataSnapshotStore(session).erase_personal_data(account_ids)
        if count and self._clear_caches:
            await self._clear_caches()
        return count

    async def mark_personal_data_updated(self, account_ids: tuple[str, ...]) -> int:
        async with self._database.session() as session:
            count = await PersonalDataSnapshotStore(session).mark_personal_data_updated(account_ids)
        if count and self._clear_caches:
            await self._clear_caches()
        return count

    async def coverage(self) -> dict[str, int]:
        async with self._database.session() as session:
            return await PersonalDataSnapshotStore(session).coverage()


class PostgresPersonalDataReportingLock(PersonalDataReportingLockPort):
    def __init__(self, database: Database) -> None:
        self._database = database

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[bool]:
        async with self._database.session() as session:
            acquired = await session.scalar(text("SELECT pg_try_advisory_xact_lock(20261016, 1900)"))
            yield bool(acquired)
