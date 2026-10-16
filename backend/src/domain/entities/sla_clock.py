# backend/src/domain/entities/sla_clock.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.sla_violation_report import SlaStatusDuration


@dataclass(frozen=True)
class SlaClockWorkingTime:
    weekday: int
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class SlaClockHoliday:
    day: date
    recurring: bool = False


@dataclass(frozen=True)
class SlaClockCalendar:
    id: str
    name: str
    timezone: str
    working_times: tuple[SlaClockWorkingTime, ...]
    holidays: tuple[SlaClockHoliday, ...] = ()


@dataclass(frozen=True)
class SlaClockAllocation:
    durations: tuple[SlaStatusDuration, ...] | None
    calendar_names: tuple[str, ...] = ()
    warning: str | None = None
