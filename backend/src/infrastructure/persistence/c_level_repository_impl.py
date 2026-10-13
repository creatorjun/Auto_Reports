# backend/src/infrastructure/persistence/c_level_repository_impl.py
from collections.abc import Callable
from copy import deepcopy
from datetime import date, datetime
from typing import Any, AsyncContextManager

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.c_level_repository import CLevelRepository
from src.domain.entities.c_level_history import CLevelComment, CLevelSnapshotSummary
from src.infrastructure.persistence.c_level_models import CLevelCommentORM, CLevelSnapshotORM


class CLevelRepositoryImpl(CLevelRepository):
    def __init__(self, session: Callable[[], AsyncContextManager[AsyncSession]]) -> None:
        self._session = session

    @staticmethod
    def _comment(row: CLevelCommentORM) -> CLevelComment:
        return CLevelComment(
            issue_key=row.issue_key, delay_reason=row.delay_reason, action_taken=row.action_taken,
            prevention_plan=row.prevention_plan, included=row.included,
            updated_by=row.updated_by, updated_at=row.updated_at.isoformat(),
        )

    @staticmethod
    def _summary(row: Any) -> CLevelSnapshotSummary:
        return CLevelSnapshotSummary(
            id=row.id, title=row.title, period=row.period, start_date=row.start_date.isoformat(),
            end_date=row.end_date.isoformat(), as_of=row.as_of.isoformat(),
            saved_by=row.saved_by, saved_at=row.saved_at.isoformat(),
        )

    async def get_comments(self, issue_keys: list[str]) -> list[CLevelComment]:
        if not issue_keys:
            return []
        async with self._session() as session:
            rows = await session.scalars(select(CLevelCommentORM).where(CLevelCommentORM.issue_key.in_(issue_keys)))
            return [self._comment(row) for row in rows]

    async def save_comment(self, comment: CLevelComment) -> CLevelComment:
        values = {
            "issue_key": comment.issue_key, "delay_reason": comment.delay_reason,
            "action_taken": comment.action_taken, "prevention_plan": comment.prevention_plan,
            "included": comment.included, "updated_by": comment.updated_by,
            "updated_at": datetime.fromisoformat(comment.updated_at),
        }
        statement = insert(CLevelCommentORM).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[CLevelCommentORM.issue_key],
            set_={key: value for key, value in values.items() if key != "issue_key"},
        )
        async with self._session() as session:
            await session.execute(statement)
        return comment

    async def save_snapshot(self, payload: dict[str, Any], title: str, actor: str) -> CLevelSnapshotSummary:
        row = CLevelSnapshotORM(
            title=title, period=payload["period"], start_date=date.fromisoformat(payload["start_date"]),
            end_date=date.fromisoformat(payload["end_date"]), as_of=datetime.fromisoformat(payload["as_of"]),
            saved_by=actor, payload=deepcopy(payload),
        )
        async with self._session() as session:
            session.add(row)
            await session.flush()
            await session.refresh(row, attribute_names=["saved_at"])
            summary = self._summary(row)
        return summary

    async def list_snapshots(self, limit: int, offset: int) -> list[CLevelSnapshotSummary]:
        columns = [getattr(CLevelSnapshotORM, name) for name in CLevelSnapshotSummary.__dataclass_fields__]
        statement = select(*columns).order_by(CLevelSnapshotORM.saved_at.desc(), CLevelSnapshotORM.id.desc()).limit(limit).offset(offset)
        async with self._session() as session:
            rows = (await session.execute(statement)).all()
            return [self._summary(row) for row in rows]

    async def get_snapshot(self, snapshot_id: int) -> tuple[CLevelSnapshotSummary, dict[str, Any]] | None:
        async with self._session() as session:
            row = await session.get(CLevelSnapshotORM, snapshot_id)
            return (self._summary(row), deepcopy(row.payload)) if row is not None else None
