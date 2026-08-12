# backend/src/domain/entities/report.py
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.ai_analysis import AiAnalysis


@dataclass(frozen=True)
class NewReport:
    week_start: date
    week_end: date
    report_date: str
    widgets: dict = field(default_factory=dict)
    ai_analysis: Optional[AiAnalysis] = None


@dataclass(frozen=True)
class Report(NewReport):
    id: int = 0
    created_at: Optional[datetime] = None
