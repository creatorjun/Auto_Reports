# backend/src/infrastructure/persistence/issue_management_snapshot_repository.py
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.dialects.postgresql import JSONB, insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, mapped_column

from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot, IssueManagementSnapshotPort
from src.application.services.snapshot_personal_data import utc
from src.domain.entities.widget_data import RecentIssueDetail
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.models import Base
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes, suppress_erased_people


class IssueManagementSnapshotORM(Base):
    __tablename__ = "issue_management_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    full_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)


class IssueManagementSnapshotRepository(IssueManagementSnapshotPort):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def load(self, project_key: str) -> IssueManagementSnapshot | None:
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            row = (await session.execute(select(IssueManagementSnapshotORM).where(
                IssueManagementSnapshotORM.project_key == project_key,
            ))).scalar_one_or_none()
            if row is None:
                return None
            payload = deepcopy(row.payload)
            if await suppress_erased_people(session, payload):
                row.payload = payload
                await session.flush()
            return self._snapshot(row)

    async def save(self, project_key: str, snapshot: IssueManagementSnapshot) -> IssueManagementSnapshot:
        payload = {"issues": [asdict(issue) for issue in snapshot.issues]}
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            await suppress_erased_people(session, payload)
            values = dict(
                project_key=project_key, synced_at=utc(snapshot.synced_at),
                full_synced_at=utc(snapshot.full_synced_at), payload=payload,
            )
            insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else postgres_insert
            statement = insert(IssueManagementSnapshotORM).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["project_key"], set_=values,
                where=IssueManagementSnapshotORM.synced_at < statement.excluded.synced_at,
            )
            await session.execute(statement)
            row = (await session.execute(select(IssueManagementSnapshotORM).where(
                IssueManagementSnapshotORM.project_key == project_key,
            ))).scalar_one()
            stored_payload = deepcopy(row.payload)
            if await suppress_erased_people(session, stored_payload):
                row.payload = stored_payload
                await session.flush()
            return self._snapshot(row)

    @staticmethod
    def _snapshot(row: IssueManagementSnapshotORM) -> IssueManagementSnapshot:
        return IssueManagementSnapshot(
            issues=tuple(RecentIssueDetail(**issue) for issue in row.payload["issues"]),
            synced_at=utc(row.synced_at), full_synced_at=utc(row.full_synced_at),
        )
