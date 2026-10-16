# backend/src/domain/entities/sla_violation_report.py
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.sla_clock import SlaClockCalendar

SlaViolationPeriod = Literal["week", "month", "year"]
SlaViolationMetric = Literal["initial_response", "resolution"]


@dataclass(frozen=True)
class SlaViolationChange:
    changed_at: datetime
    from_status: str
    to_status: str


@dataclass(frozen=True)
class SlaViolationCycle:
    metric: SlaViolationMetric
    breached_at: datetime | None
    breached: bool = True
    ongoing: bool = False
    paused: bool | None = None
    goal_ms: int | None = None
    elapsed_ms: int | None = None
    exceeded_ms: int | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    status: str | None = None


@dataclass(frozen=True)
class SlaViolationIssue:
    key: str
    summary: str
    created_at: datetime
    current_status: str
    customer: str | None
    partners: tuple[str, ...] | None
    reporter: str | None
    assignee: str | None
    tac_assignee: str | None
    cycles: tuple[SlaViolationCycle, ...]
    changes: tuple[SlaViolationChange, ...] = ()
    history_complete: bool = True
    warnings: tuple[str, ...] = ()
    issue_type: str | None = None
    clock_calendars: tuple["SlaClockCalendar", ...] = ()
    clock_snapshot_before: datetime | None = None
    clock_snapshot_after: datetime | None = None
    clock_pause_statuses: tuple[str, ...] = ("결과 대기 중", "자료 요청 중", "보류 중")
    reporter_account_id: str | None = None
    assignee_account_id: str | None = None
    tac_assignee_account_id: str | None = None
    personal_data_retrieved_at: str | None = None


@dataclass(frozen=True)
class SlaViolationBreach:
    metric: SlaViolationMetric
    breached_at: datetime | None
    status: str | None


@dataclass(frozen=True)
class SlaStatusDuration:
    status: str
    hours: float


@dataclass(frozen=True)
class SlaViolationTicket:
    key: str
    summary: str
    created_at: datetime
    elapsed_days: int
    customer: str | None
    partners: tuple[str, ...] | None
    reporter: str | None
    assignee: str | None
    tac_assignee: str | None
    current_status: str
    status_durations: tuple[SlaStatusDuration, ...] | None
    breaches: tuple[SlaViolationBreach, ...]
    warnings: tuple[str, ...] = ()
    issue_type: str | None = None
    sla_cycles: tuple[SlaViolationCycle, ...] | None = None
    status_durations_basis: Literal["wall_clock", "resolution_sla"] = "wall_clock"
    status_duration_calendar: str | None = None
    reporter_account_id: str | None = None
    assignee_account_id: str | None = None
    tac_assignee_account_id: str | None = None
    personal_data_retrieved_at: str | None = None


@dataclass(frozen=True)
class SlaViolationReportSummary:
    id: int
    period: SlaViolationPeriod
    selected_date: date
    start_date: date
    end_date: date
    generated_at: datetime
    generated_by: str
    ticket_count: int
    initial_response_count: int
    resolution_count: int


@dataclass(frozen=True)
class SlaViolationReport(SlaViolationReportSummary):
    tickets: tuple[SlaViolationTicket, ...]
    warnings: tuple[str, ...] = ()
