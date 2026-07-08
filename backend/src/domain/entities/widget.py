# backend/src/domain/entities/widget.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class WidgetResult(Generic[T]):
    name: str
    total: int
    jql: str = ""
    data: T | None = None
