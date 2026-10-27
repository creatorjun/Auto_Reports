# backend/src/application/services/report_period.py
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Literal

from src.domain.constants import KST


ReportPeriod = Literal["day", "week", "month", "year"]


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
