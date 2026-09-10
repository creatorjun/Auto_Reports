# backend/src/application/services/issue_age.py
from dataclasses import replace
from datetime import datetime

from src.domain.constants import KST
from src.domain.entities.report import Report
from src.domain.entities.widget_data import RecentIssueWidgetData, SimpleIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId


def _created_at_kst(created: str | None) -> datetime | None:
    if not created:
        return None
    try:
        value = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def issue_elapsed_days(created: str | None, now: datetime) -> int:
    created_at = _created_at_kst(created)
    if created_at is None:
        return 0
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    return max(0, (now.astimezone(KST).date() - created_at.date()).days)


def issue_created_display(created: str | None) -> str:
    created_at = _created_at_kst(created)
    return created_at.strftime("%Y-%m-%d %H:%M") if created_at else ""


def with_current_issue_age(report: Report | None, now: datetime | None = None) -> Report | None:
    if report is None:
        return None
    now = now or datetime.now(KST)
    widgets = dict(report.widgets)
    for widget_id in (
        WidgetId.ISSUE_REVIEW,
        WidgetId.DATA_REQUEST,
        WidgetId.RESULT_PENDING,
        WidgetId.RECENT_ISSUES,
    ):
        widget = widgets.get(widget_id)
        if widget is None or not isinstance(widget.data, (RecentIssueWidgetData, SimpleIssueWidgetData)):
            continue
        details = [
            replace(issue, elapsed_days=issue_elapsed_days(issue.created, now))
            for issue in widget.data.issue_details
        ]
        widgets[widget_id] = replace(widget, data=replace(widget.data, issue_details=details))
    return replace(report, widgets=widgets)
