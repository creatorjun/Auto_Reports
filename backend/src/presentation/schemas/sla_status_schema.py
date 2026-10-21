# backend/src/presentation/schemas/sla_status_schema.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.presentation.schemas.sla_violation_schema import SlaStatusDurationSchema


class SlaStatusMetricSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sla_id: str
    sla_name: str
    goal_millis: int = Field(gt=0)
    remaining_millis: int = Field(ge=0)
    remaining_percent: float = Field(ge=0, lt=30)
    paused: bool


class SlaStatusTicketSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    summary: str
    status: str
    assignee: str
    slas: tuple[SlaStatusMetricSchema, ...]
    created_at: datetime | None = None
    elapsed_days: int | None = None
    customer: str | None = None
    partners: tuple[str, ...] | None = None
    reporter: str | None = None
    tac_assignee: str | None = None
    issue_type: str | None = None
    status_durations: tuple[SlaStatusDurationSchema, ...] | None = None
    status_durations_basis: Literal["resolution_sla"] = "resolution_sla"
    status_duration_calendar: str | None = None
    warnings: tuple[str, ...] = ()


class SlaStatusSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    threshold_percent: Literal[30]
    ticket_count: int = Field(ge=0)
    sla_count: int = Field(ge=0)
    tickets: tuple[SlaStatusTicketSchema, ...]
