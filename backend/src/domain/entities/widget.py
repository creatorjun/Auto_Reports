# backend/src/domain/entities/widget.py
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WidgetResult:
    name: str
    total: int
    jql: str = ""
    breakdown: dict[str, Any] = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)
