# backend/src/domain/entities/report.py
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.ai_analysis import AiAnalysis


@dataclass(frozen=True)
class NewReport:
    """DB 저장 전 상태의 보고서. id가 없다."""
    week_start: date
    week_end: date
    report_date: str
    widgets: dict = field(default_factory=dict)
    ai_analysis: Optional[AiAnalysis] = None


@dataclass(frozen=True)
class Report(NewReport):
    """DB 저장 완료 후 식별자를 가진 보고서."""
    id: int = 0
    created_at: Optional[datetime] = None
