# backend/src/application/services/c_level_periods.py
import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from src.domain.constants import KST


def local_time(value: datetime) -> datetime:
    return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)


def shift_months(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


@dataclass(frozen=True)
class CLevelWindow:
    start: datetime
    end: datetime

    @property
    def start_date(self) -> str:
        return self.start.date().isoformat()

    @property
    def end_date(self) -> str:
        return max(self.start.date(), (self.end - timedelta(microseconds=1)).date()).isoformat()


def report_windows(period: str, end_date: date | None, now: datetime) -> tuple[CLevelWindow, CLevelWindow, tuple[CLevelWindow, ...]]:
    now = local_time(now)
    selected = end_date or now.date()
    if period not in {"week", "month"}:
        raise ValueError("보고 주기는 week 또는 month여야 합니다.")
    if selected > now.date():
        raise ValueError("미래 날짜의 보고서는 조회할 수 없습니다.")
    if period == "week":
        start = datetime.combine(selected - timedelta(days=6), time.min, KST)
        full_end = datetime.combine(selected + timedelta(days=1), time.min, KST)
        end = min(full_end, now)
        current = CLevelWindow(start, end)
        previous = CLevelWindow(start - timedelta(days=7), end - timedelta(days=7))
        trend = tuple(
            CLevelWindow(start - timedelta(days=7 * offset), end if offset == 0 else start - timedelta(days=7 * (offset - 1)))
            for offset in reversed(range(8))
        )
    else:
        start = datetime.combine(selected.replace(day=1), time.min, KST)
        full_end = shift_months(start, 1)
        end = min(full_end, now)
        current = CLevelWindow(start, end)
        previous = CLevelWindow(shift_months(start, -1), start if end == full_end else shift_months(end, -1))
        trend = tuple(
            CLevelWindow(shift_months(start, -offset), end if offset == 0 else shift_months(start, 1 - offset))
            for offset in reversed(range(8))
        )
    return current, previous, trend


def age_bucket(created_at: datetime, as_of: datetime) -> str | None:
    created = local_time(created_at)
    reference = local_time(as_of) - timedelta(microseconds=1)
    if shift_months(created, 12).date() <= reference.date():
        return "12+"
    if shift_months(created, 6).date() <= reference.date():
        return "6-12"
    if shift_months(created, 3).date() <= reference.date():
        return "3-6"
    if shift_months(created, 1).date() <= reference.date():
        return "1-3"
    return None
