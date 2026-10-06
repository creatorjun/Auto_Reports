# backend/src/application/use_cases/notify_todo_issues.py
import logging
from collections.abc import Mapping
from datetime import datetime

from src.application.ports.email_port import EmailPort
from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.services.issue_type_policy import is_license_issue_type
from src.domain.constants import KST
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)

TODO_STATUSES = {"\ud560 \uc77c", "\uc7ac\uc624\ud508"}


def extract_todo_issues(
    widgets: Mapping[WidgetId, WidgetResult],
) -> list[RecentIssueDetail]:
    recent_result = widgets.get(WidgetId.RECENT_ISSUES)
    if recent_result is None:
        return []
    data = recent_result.data
    if not isinstance(data, RecentIssueWidgetData):
        return []
    return [
        detail for detail in data.issue_details
        if detail.status in TODO_STATUSES and not is_license_issue_type(detail.type)
    ]


class NotifyTodoIssuesUseCase:
    def __init__(
        self,
        email: EmailPort,
        notify_to: list[str],
        jira_base_url: str,
        renderer: IssueNotificationRendererPort,
    ) -> None:
        self._renderer = renderer
        self._email = email
        self._notify_to = notify_to
        self._jira_base_url = jira_base_url
        self._notified_keys: set[str] = set()

    def clear_resolved(self, current_todo_keys: set[str]) -> None:
        resolved = self._notified_keys - current_todo_keys
        if resolved:
            logger.info(f"[NotifyTodoIssues] \ud574\uc18c\ub41c \uc774\uc288 \uc13c\ud2f8\ub10c \uc81c\uac70: {resolved}")
            self._notified_keys -= resolved

    async def execute(self, todo_issues: list[RecentIssueDetail]) -> None:
        if not todo_issues:
            return

        current_keys = {issue.key for issue in todo_issues}
        self.clear_resolved(current_keys)

        new_issues = [
            issue for issue in todo_issues if issue.key not in self._notified_keys
        ]

        if not new_issues:
            excluded = str(self._notified_keys) if self._notified_keys else "없음"
            logger.info(f"[NotifyTodoIssues] 신규 할일 없음 (이미 알림 {len(self._notified_keys)}건 제외: {excluded})")
            return

        keys_str = ", ".join(issue.key for issue in new_issues)
        subject = f"[TAC] \ud560\uc77c \uc774\uc288: {keys_str}"
        body = self._renderer.render_todo(new_issues, self._jira_base_url, datetime.now(KST))
        excluded_str = str(self._notified_keys) if self._notified_keys else "없음"
        logger.info(f"[NotifyTodoIssues] 신규 {len(new_issues)}건 메일 발송 → {self._notify_to} (제외: {excluded_str})")
        await self._email.send(to=self._notify_to, subject=subject, body=body)

        self._notified_keys.update(issue.key for issue in new_issues)
