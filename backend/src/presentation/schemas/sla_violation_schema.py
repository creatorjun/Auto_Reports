# backend/src/presentation/schemas/sla_violation_schema.py
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SlaViolationCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal["week", "month", "year"]
    date: date


class SlaViolationBreachSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: Literal["initial_response", "resolution"]
    breached_at: datetime | None
    status: str | None


class SlaStatusDurationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    hours: float


class SlaViolationTicketSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    status_durations: tuple[SlaStatusDurationSchema, ...] | None
    breaches: tuple[SlaViolationBreachSchema, ...]
    warnings: tuple[str, ...] = ()


class SlaViolationReportSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period: Literal["week", "month", "year"]
    selected_date: date
    start_date: date
    end_date: date
    generated_at: datetime
    generated_by: str
    ticket_count: int
    initial_response_count: int
    resolution_count: int


class SlaViolationReportSchema(SlaViolationReportSummarySchema):
    tickets: tuple[SlaViolationTicketSchema, ...]
    warnings: tuple[str, ...] = ()
