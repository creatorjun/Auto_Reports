# backend/src/infrastructure/persistence/redeployment_repository_impl.py
from dataclasses import asdict, replace
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, select, text
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.constants import KST
from src.domain.entities.redeployment_report import REDEPLOYMENT_START, RedeploymentReport, RedeploymentTicket
from src.infrastructure.persistence.models import Base


class RedeploymentReportORM(Base):
    __tablename__ = "redeployment_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RedeploymentRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_generation_lock(self) -> bool:
        result = await self._session.execute(text("SELECT pg_try_advisory_xact_lock(20260101, 800)"))
        return bool(result.scalar())

    async def get_latest(self) -> RedeploymentReport | None:
        result = await self._session.execute(select(RedeploymentReportORM).order_by(RedeploymentReportORM.generated_at.desc()).limit(1))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        payload = row.payload
        return RedeploymentReport(
            id=row.id, period_start=date.fromisoformat(payload.get("period_start", str(REDEPLOYMENT_START))),
            generated_at=row.generated_at, generated_by=row.generated_by, source_jql=payload["source_jql"],
            tickets=tuple(RedeploymentTicket(**{**item, "partners": tuple(item["partners"])}) for item in payload["tickets"]),
            warnings=tuple(payload.get("warnings", [])),
        )

    async def save(self, report: RedeploymentReport) -> RedeploymentReport:
        values = dict(
            snapshot_date=report.generated_at.astimezone(KST).date(), generated_at=report.generated_at,
            generated_by=report.generated_by, payload={
                "period_start": str(report.period_start), "source_jql": report.source_jql,
                "tickets": [asdict(ticket) for ticket in report.tickets], "warnings": list(report.warnings),
            },
        )
        statement = insert(RedeploymentReportORM).values(**values)
        statement = statement.on_conflict_do_update(index_elements=["snapshot_date"], set_=values).returning(RedeploymentReportORM.id)
        result = await self._session.execute(statement)
        saved = replace(report, id=result.scalar_one())
        await self._session.flush()
        return saved
