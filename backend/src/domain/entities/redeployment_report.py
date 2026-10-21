# backend/src/domain/entities/redeployment_report.py
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from src.domain.constants import KST

REDEPLOYMENT_START = date(2026, 1, 1)


def redeployment_refresh_due(now: datetime) -> datetime:
    local = now.astimezone(KST)
    due = local.replace(hour=8, minute=0, second=0, microsecond=0)
    return due if local >= due else due - timedelta(days=1)


@dataclass(frozen=True)
class RedeploymentTicket:
    key: str
    summary: str
    issue_type: str
    status: str
    closed: bool
    created_at: str
    resolved_at: str | None
    completion_month: str | None
    cause: str | None
    reason: str | None
    repatch_count: int | None
    customer: str | None
    partners: tuple[str, ...]
    assignee: str | None
    reporter: str | None
    assignee_account_id: str | None = None
    reporter_account_id: str | None = None
    personal_data_retrieved_at: str | None = None
    personal_data_field_retrieved_at: dict[str, str] | None = None


@dataclass(frozen=True)
class RedeploymentReport:
    id: int
    period_start: date
    generated_at: datetime
    generated_by: str
    source_jql: str
    tickets: tuple[RedeploymentTicket, ...]
    warnings: tuple[str, ...] = ()
