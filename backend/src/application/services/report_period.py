# backend/src/application/services/report_period.py
from calendar import monthrange
from datetime import date, datetime, time, timedelta
import re
from typing import Literal

from src.domain.constants import KST


ReportPeriod = Literal["day", "week", "month", "year", "custom"]


def custom_report_dates(start_date: str | None, end_date: str | None, today: date) -> tuple[datetime, datetime]:
    selected: list[date] = []
    for value in (start_date, end_date):
        if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("시작일과 종료일은 YYYY-MM-DD 형식으로 입력해야 합니다.")
        try:
            selected.append(date.fromisoformat(value))
        except ValueError as error:
            raise ValueError("시작일과 종료일은 올바른 날짜로 입력해야 합니다.") from error
    start, end = selected
    if start > end:
        raise ValueError("시작일은 종료일 이후로 선택할 수 없습니다.")
    if end > today:
        raise ValueError("종료일은 오늘 이후로 선택할 수 없습니다.")
    return (
        datetime.combine(start, time.min, tzinfo=KST),
        datetime.combine(end, time(23, 59, 59), tzinfo=KST),
    )


def report_period_dates(
    period: ReportPeriod,
    selected_date: date,
    today: date,
) -> tuple[datetime, datetime]:
    if selected_date > today:
        raise ValueError("기준일은 오늘 이후로 선택할 수 없습니다.")
    if period == "day":
        start = end = selected_date
    elif period == "week":
        start = selected_date - timedelta(days=selected_date.weekday())
        end = start + timedelta(days=6)
    elif period == "month":
        start = selected_date.replace(day=1)
        end = selected_date.replace(day=monthrange(selected_date.year, selected_date.month)[1])
    elif period == "year":
        start = selected_date.replace(month=1, day=1)
        end = selected_date.replace(month=12, day=31)
    else:
        raise ValueError("지원하지 않는 보고서 기간입니다.")
    return (
        datetime.combine(start, time.min, tzinfo=KST),
        datetime.combine(end, time(23, 59, 59), tzinfo=KST),
    )
