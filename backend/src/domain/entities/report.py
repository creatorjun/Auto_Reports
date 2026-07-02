# backend/src/domain/entities/report.py
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.ai_analysis import AiAnalysis


@dataclass
class Report:
    id: Optional[int]
    week_start: date
    week_end: date
    report_date: str
    widgets: dict[str, WidgetResult] = field(default_factory=dict)
    ai_analysis: Optional[AiAnalysis] = None
    created_at: Optional[datetime] = None
