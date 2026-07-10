# backend/src/presentation/schemas/report_schema.py
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class AiAnalysisSchema(BaseModel):
    summary: str
    risks: list[str]
    recommendations: list[str]
    sentiment: str


class WidgetResultSchema(BaseModel):
    name: str
    total: int
    jql: str = ""
    data: Optional[dict[str, Any]] = None


class ReportSummarySchema(BaseModel):
    id: int
    week_start: date
    week_end: date
    report_date: str
    created_at: datetime
    sentiment: Optional[str] = None


class ReportDetailSchema(BaseModel):
    id: int
    week_start: date
    week_end: date
    report_date: str
    created_at: datetime
    widgets: dict[str, WidgetResultSchema]
    ai_analysis: Optional[AiAnalysisSchema] = None


class TriggerRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class TriggerAcceptedSchema(BaseModel):
    job_id: str
    message: str


class JobStatusSchema(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    report_id: Optional[int] = None
    error: Optional[str] = None
