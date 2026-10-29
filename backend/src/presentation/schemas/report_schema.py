# backend/src/presentation/schemas/report_schema.py
from datetime import date, datetime
from datetime import date as SelectedDate
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.application.services.report_period import ReportPeriod


class AiAnalysisSchema(BaseModel):
    summary: str
    risks: list[str]
    recommendations: list[str]
    sentiment: str
    bottlenecks: list[str] = Field(default_factory=list)
    provider: str | None = None
    analyzed_at: str | None = None
    is_stale: bool = False


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
    scope: Literal["standard", "annual"] = "standard"
    report_year: Optional[int] = None


class ReportDetailSchema(BaseModel):
    id: int
    week_start: date
    week_end: date
    report_date: str
    created_at: datetime
    widgets: dict[str, WidgetResultSchema]
    ai_analysis: Optional[AiAnalysisSchema] = None
    scope: Literal["standard", "annual"] = "standard"
    report_year: Optional[int] = None


class TriggerRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period: ReportPeriod | None = None
    date: SelectedDate | None = None
    rerun_latest: bool = False

    @model_validator(mode="after")
    def validate_period_selection(self) -> "TriggerRequest":
        if self.rerun_latest and any(
            value is not None
            for value in (self.period, self.date, self.start_date, self.end_date)
        ):
            raise ValueError("최근 보고서 갱신과 기간 선택을 함께 입력할 수 없습니다.")
        if self.period == "custom":
            if self.date is not None or self.start_date is None or self.end_date is None:
                raise ValueError("사용자 지정 기간은 시작일과 종료일만 함께 입력해야 합니다.")
        else:
            if (self.period is None) != (self.date is None):
                raise ValueError("period와 date를 함께 입력해야 합니다.")
            if self.period is not None and (self.start_date is not None or self.end_date is not None):
                raise ValueError("기간 선택과 시작일/종료일을 함께 입력할 수 없습니다.")
        return self


class TriggerAcceptedSchema(BaseModel):
    job_id: str
    message: str


class JobStatusSchema(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    report_id: Optional[int] = None
    error: Optional[str] = None
    retry_after: Optional[int] = None
