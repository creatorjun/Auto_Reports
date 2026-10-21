# backend/src/infrastructure/persistence/sla_status_snapshot_repository.py
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, select
from sqlalchemy.dialects.postgresql import JSONB, insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, mapped_column

from src.application.ports.sla_status_snapshot_port import SlaStatusSnapshotPort
from src.application.services.snapshot_personal_data import utc
from src.domain.entities.sla_status import SlaStatusMetric, SlaStatusSnapshot, SlaStatusTicket
from src.domain.entities.sla_violation_report import SlaStatusDuration
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.models import Base
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes, suppress_erased_people


class SlaStatusSnapshotORM(Base):
    __tablename__ = "sla_status_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)


class SlaStatusSnapshotRepository(SlaStatusSnapshotPort):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def load(self, project_key: str) -> SlaStatusSnapshot | None:
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            row = (await session.execute(select(SlaStatusSnapshotORM).where(
                SlaStatusSnapshotORM.project_key == project_key,
            ))).scalar_one_or_none()
            if row is None:
                return None
            payload = deepcopy(row.payload)
            if await suppress_erased_people(session, payload):
                row.payload = payload
                await session.flush()
            return self._snapshot(row)

    async def save(self, project_key: str, snapshot: SlaStatusSnapshot) -> SlaStatusSnapshot:
        tickets = [asdict(ticket) for ticket in snapshot.tickets]
        for ticket in tickets:
            if ticket["created_at"] is not None:
                ticket["created_at"] = ticket["created_at"].isoformat()
        payload = {
            "threshold_percent": snapshot.threshold_percent, "ticket_count": snapshot.ticket_count,
            "sla_count": snapshot.sla_count, "tickets": tickets,
        }
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            await suppress_erased_people(session, payload)
            values = dict(project_key=project_key, generated_at=utc(snapshot.generated_at), payload=payload)
            insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else postgres_insert
            statement = insert(SlaStatusSnapshotORM).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["project_key"], set_=values,
                where=SlaStatusSnapshotORM.generated_at < statement.excluded.generated_at,
            )
            await session.execute(statement)
            row = (await session.execute(select(SlaStatusSnapshotORM).where(
                SlaStatusSnapshotORM.project_key == project_key,
            ))).scalar_one()
            stored_payload = deepcopy(row.payload)
            if await suppress_erased_people(session, stored_payload):
                row.payload = stored_payload
                await session.flush()
            return self._snapshot(row)

    @staticmethod
    def _snapshot(row: SlaStatusSnapshotORM) -> SlaStatusSnapshot:
        tickets = []
        for raw in row.payload["tickets"]:
            ticket = deepcopy(raw)
            ticket["slas"] = tuple(SlaStatusMetric(**sla) for sla in ticket["slas"])
            if ticket.get("created_at") is not None:
                ticket["created_at"] = datetime.fromisoformat(ticket["created_at"])
            if ticket.get("status_durations") is not None:
                ticket["status_durations"] = tuple(SlaStatusDuration(**duration) for duration in ticket["status_durations"])
            for name in ("partners", "warnings"):
                if ticket.get(name) is not None:
                    ticket[name] = tuple(ticket[name])
            tickets.append(SlaStatusTicket(**ticket))
        return SlaStatusSnapshot(
            generated_at=utc(row.generated_at), threshold_percent=row.payload["threshold_percent"],
            ticket_count=row.payload["ticket_count"], sla_count=row.payload["sla_count"], tickets=tuple(tickets),
        )
