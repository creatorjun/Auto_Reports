# backend/src/presentation/schemas/report_chart_schema.py
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportChartIssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    summary: str
    type: str
    status: str | None = None
    created: str | None = None
    resolved: str | None = None
    elapsed_hours: float | None = None
    sla_met: bool | None = None
    month: str | None = None
    cause: str | None = None
    assignee: str | None = None
    partners: list[str] = Field(default_factory=list)
    priority: str | None = None


class ReportChartIssueResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issues: list[ReportChartIssueSchema]
    snapshot_count: int | None
    current_count: int
    source_total: int
    source_total_exact: bool
    collection_limit: int | None
    truncated: bool
    queried_at: str
    snapshot_at: str
    source: Literal["current_jira"]
