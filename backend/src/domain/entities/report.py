# backend/src/domain/entities/report.py
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.ai_analysis import AiAnalysis


class ReportScope(str, Enum):
    STANDARD = "standard"
    ANNUAL = "annual"


@dataclass(frozen=True)
class NewReport:
    week_start: date
    week_end: date
    report_date: str
    widgets: dict = field(default_factory=dict)
    ai_analysis: Optional[AiAnalysis] = None
    scope: ReportScope = ReportScope.STANDARD
    report_year: Optional[int] = None


@dataclass(frozen=True)
class Report(NewReport):
    id: int = 0
    created_at: Optional[datetime] = None
