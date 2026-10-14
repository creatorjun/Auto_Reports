# backend/src/infrastructure/persistence/sla_violation_repository_impl.py
from dataclasses import asdict, fields, replace
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.sla_violation_port import SlaViolationRepository
from src.domain.entities.sla_violation_report import (
    SlaStatusDuration,
    SlaViolationBreach,
    SlaViolationMetric,
    SlaViolationPeriod,
    SlaViolationReport,
    SlaViolationReportSummary,
    SlaViolationTicket,
)
from src.infrastructure.persistence.sla_violation_models import SlaViolationReportORM


def _serialize_ticket(ticket: SlaViolationTicket) -> dict:
    result = asdict(ticket)
    result["created_at"] = ticket.created_at.isoformat()
    result["breaches"] = [
        {
            "metric": breach.metric,
            "breached_at": breach.breached_at.isoformat() if breach.breached_at else None,
            "status": breach.status,
        }
        for breach in ticket.breaches
    ]
    return result


def _deserialize_ticket(payload: dict) -> SlaViolationTicket:
    durations = payload["status_durations"]
    partners = payload["partners"]
    return SlaViolationTicket(
        key=payload["key"],
        summary=payload["summary"],
        created_at=datetime.fromisoformat(payload["created_at"]),
        elapsed_days=payload["elapsed_days"],
        customer=payload["customer"],
        partners=tuple(partners) if partners is not None else None,
        reporter=payload["reporter"],
        assignee=payload["assignee"],
        tac_assignee=payload["tac_assignee"],
        current_status=payload["current_status"],
        status_durations=tuple(SlaStatusDuration(**duration) for duration in durations) if durations is not None else None,
        breaches=tuple(
            SlaViolationBreach(
                metric=cast(SlaViolationMetric, breach["metric"]),
                breached_at=datetime.fromisoformat(breach["breached_at"]) if breach["breached_at"] else None,
                status=breach["status"],
            )
            for breach in payload["breaches"]
        ),
        warnings=tuple(payload.get("warnings", ())),
    )


class SlaViolationRepositoryImpl(SlaViolationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: SlaViolationReport) -> SlaViolationReport:
        metadata = {field.name: getattr(report, field.name) for field in fields(SlaViolationReportSummary) if field.name != "id"}
        metadata["generated_at"] = report.generated_at.astimezone(timezone.utc)
        orm = SlaViolationReportORM(
            **metadata,
            payload={
                "tickets": [_serialize_ticket(ticket) for ticket in report.tickets],
                "warnings": list(report.warnings),
            },
        )
        try:
            self._session.add(orm)
            await self._session.flush()
            saved = replace(report, id=orm.id)
            await self._session.commit()
            return saved
        except BaseException:
            await self._session.rollback()
            raise

    async def get_latest(self) -> SlaViolationReport | None:
        result = await self._session.execute(
            select(SlaViolationReportORM)
            .order_by(SlaViolationReportORM.generated_at.desc(), SlaViolationReportORM.id.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return self._to_report(orm) if orm is not None else None

    async def get_by_id(self, report_id: int) -> SlaViolationReport | None:
        result = await self._session.execute(select(SlaViolationReportORM).where(SlaViolationReportORM.id == report_id))
        orm = result.scalar_one_or_none()
        return self._to_report(orm) if orm is not None else None

    async def list_summaries(self, limit: int, offset: int) -> list[SlaViolationReportSummary]:
        result = await self._session.execute(
            select(*(getattr(SlaViolationReportORM, field.name) for field in fields(SlaViolationReportSummary)))
            .order_by(SlaViolationReportORM.generated_at.desc(), SlaViolationReportORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_summary(row) for row in result.all()]

    @staticmethod
    def _to_summary(orm: object) -> SlaViolationReportSummary:
        metadata = {field.name: getattr(orm, field.name) for field in fields(SlaViolationReportSummary)}
        generated_at = metadata["generated_at"]
        if generated_at.tzinfo is None:
            metadata["generated_at"] = generated_at.replace(tzinfo=timezone.utc)
        metadata["period"] = cast(SlaViolationPeriod, metadata["period"])
        return SlaViolationReportSummary(**metadata)

    @classmethod
    def _to_report(cls, orm: SlaViolationReportORM) -> SlaViolationReport:
        return SlaViolationReport(
            **asdict(cls._to_summary(orm)),
            tickets=tuple(_deserialize_ticket(ticket) for ticket in orm.payload["tickets"]),
            warnings=tuple(orm.payload.get("warnings", ())),
        )
