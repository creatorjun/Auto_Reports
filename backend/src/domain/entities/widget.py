# backend/src/domain/entities/widget.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from src.domain.entities.widget_data import AiContextProvider

T = TypeVar("T")


@dataclass
class WidgetResult(Generic[T]):
    name: str
    total: int
    jql: str = ""
    data: T | None = None

    def ai_context(self) -> dict:
        if isinstance(self.data, AiContextProvider):
            return self.data.to_ai_context()
        return {}
