# backend/src/infrastructure/persistence/personal_data_snapshot_store.py
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.personal_data_port import PersonalDataSnapshotPort
from src.application.services.snapshot_personal_data import aggregate_gaps, erase_snapshot_people, snapshot_people
from src.domain.entities.personal_data import PersonalDataAccount
from src.infrastructure.persistence.models import ReportORM
from src.infrastructure.persistence.issue_management_snapshot_repository import IssueManagementSnapshotORM
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes
from src.infrastructure.persistence.redeployment_repository_impl import RedeploymentReportORM
from src.infrastructure.persistence.sla_violation_models import SlaViolationReportORM


@dataclass
class SnapshotDocument:
    kind: str
    row_id: int
    generated_at: datetime
    payload: dict
    row: object
    attribute: str


class PersonalDataSnapshotStore(PersonalDataSnapshotPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.erased_report_ids: tuple[int, ...] = ()

    async def documents(self, lock: bool = False) -> list[SnapshotDocument]:
        documents = []
        for model, kind, attribute, timestamp in (
            (ReportORM, "dashboard", "widgets", "created_at"),
            (SlaViolationReportORM, "sla", "payload", "generated_at"),
            (RedeploymentReportORM, "redeployment", "payload", "generated_at"),
            (IssueManagementSnapshotORM, "issue_management", "payload", "synced_at"),
        ):
            statement = select(model).order_by(model.id)
            if lock:
                statement = statement.with_for_update()
            rows = (await self._session.execute(statement)).scalars().all()
            documents.extend(SnapshotDocument(kind, row.id, getattr(row, timestamp), deepcopy(getattr(row, attribute)), row, attribute) for row in rows)
        return documents

    async def collect_accounts(self) -> tuple[PersonalDataAccount, ...]:
        oldest: dict[str, datetime] = {}
        for document in await self.documents():
            for person in snapshot_people(document.payload, document.generated_at):
                if person.account_id is not None:
                    oldest[person.account_id] = min(oldest.get(person.account_id, person.retrieved_at), person.retrieved_at)
        return tuple(PersonalDataAccount(account_id, timestamp) for account_id, timestamp in sorted(oldest.items()))

    async def coverage(self) -> dict[str, int]:
        known: set[str] = set()
        unknown = 0
        for document in await self.documents():
            for person in snapshot_people(document.payload, document.generated_at):
                if person.account_id is None:
                    unknown += 1
                else:
                    known.add(person.account_id)
            unknown += aggregate_gaps(document.payload)
        return {"known_accounts": len(known), "unmapped_personal_fields": unknown}

    async def erase_personal_data(self, account_ids: tuple[str, ...]) -> int:
        affected = 0
        report_ids = []
        if not account_ids:
            return affected
        await lock_personal_data_writes(self._session)
        for document in await self.documents(lock=True):
            if erase_snapshot_people(document.payload, set(account_ids)):
                setattr(document.row, document.attribute, document.payload)
                affected += 1
                if document.kind == "dashboard":
                    report_ids.append(document.row_id)
        self.erased_report_ids = tuple(report_ids)
        await self._session.flush()
        return affected

    async def save_identity_metadata(self, documents: list[SnapshotDocument]) -> None:
        for document in documents:
            setattr(document.row, document.attribute, document.payload)
        await self._session.flush()
