# backend/src/domain/entities/sla_status.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.domain.entities.sla_violation_report import SlaStatusDuration


@dataclass(frozen=True)
class SlaStatusMetric:
    sla_id: str
    sla_name: str
    goal_millis: int
    remaining_millis: int
    remaining_percent: float
    paused: bool


@dataclass(frozen=True)
class SlaStatusTicket:
    key: str
    summary: str
    status: str
    assignee: str
    slas: tuple[SlaStatusMetric, ...]
    created_at: datetime | None = None
    elapsed_days: int | None = None
    customer: str | None = None
    partners: tuple[str, ...] | None = None
    reporter: str | None = None
    tac_assignee: str | None = None
    issue_type: str | None = None
    status_durations: tuple[SlaStatusDuration, ...] | None = None
    status_durations_basis: Literal["resolution_sla"] = "resolution_sla"
    status_duration_calendar: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SlaStatusSnapshot:
    generated_at: datetime
    threshold_percent: int
    ticket_count: int
    sla_count: int
    tickets: tuple[SlaStatusTicket, ...]
