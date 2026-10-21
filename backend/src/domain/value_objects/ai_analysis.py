# backend/src/domain/value_objects/ai_analysis.py
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class AiAnalysis:
    summary: str
    risks: list[str]
    recommendations: list[str]
    sentiment: Literal["good", "warning", "critical"]
    bottlenecks: list[str] = field(default_factory=list)
    provider: str | None = None
    analyzed_at: str | None = None
    is_stale: bool = False
