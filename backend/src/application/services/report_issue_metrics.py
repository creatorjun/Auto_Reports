# backend/src/application/services/report_issue_metrics.py
from datetime import datetime

from src.application.services.stage_duration import parse_timestamp


def resolution_elapsed(created: str, resolved: str, now: datetime) -> tuple[float, int] | None:
    if not created:
        return None
    try:
        end = parse_timestamp(resolved) if resolved else parse_timestamp(now.isoformat())
        hours = (end - parse_timestamp(created)).total_seconds() / 3600
    except ValueError:
        return None
    if hours < 0:
        return None
    return hours, end.month
