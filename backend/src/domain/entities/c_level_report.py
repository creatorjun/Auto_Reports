# backend/src/domain/entities/c_level_report.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CLevelStatus:
    id: str
    name: str
    category: str


@dataclass(frozen=True)
class CLevelStatusChange:
    changed_at: datetime
    from_status: CLevelStatus
    to_status: CLevelStatus


@dataclass(frozen=True)
class CLevelFieldChange:
    changed_at: datetime
    field_id: str
    from_value: str | None
    to_value: str | None


@dataclass(frozen=True)
class CLevelSlaCycle:
    metric: str
    cycle_id: str
    start_at: datetime | None = None
    stop_at: datetime | None = None
    breach_at: datetime | None = None
    goal_ms: int | None = None
    elapsed_ms: int | None = None
    remaining_ms: int | None = None
    breached: bool | None = None
    paused: bool | None = None
    ongoing: bool = False


@dataclass(frozen=True)
class CLevelIssue:
    key: str
    summary: str
    issue_type: str
    created_at: datetime
    status: CLevelStatus
    updated_at: datetime | None = None
    customer_name: str = ""
    partner_names: tuple[str, ...] = ()
    reporter: str = ""
    assignee: str = ""
    tac_assignee: str = ""
    status_changes: tuple[CLevelStatusChange, ...] = ()
    sla_cycles: tuple[CLevelSlaCycle, ...] = ()
    history_complete: bool = True
    warnings: tuple[str, ...] = ()
    field_changes: tuple[CLevelFieldChange, ...] = ()
    first_response_at: datetime | None = None
    jira_delay_reason: str = ""
    jira_delay_responsibility: str = ""
