# backend/src/domain/value_objects/ai_analysis.py
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AiAnalysis:
    summary: str
    risks: list[str]
    recommendations: list[str]
    sentiment: Literal["good", "warning", "critical"]
