# backend/src/application/services/report_issue_metrics.py
from datetime import datetime


def resolution_elapsed(created: str, resolved: str, now: datetime) -> tuple[float, int] | None:
    if not created:
        return None
    end = datetime.fromisoformat(resolved[:19]) if resolved else now
    hours = (end - datetime.fromisoformat(created[:19])).total_seconds() / 3600
    return hours, end.month
