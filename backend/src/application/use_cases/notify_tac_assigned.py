# backend/src/application/use_cases/notify_tac_assigned.py
import logging
from collections.abc import Mapping
from datetime import datetime

from src.application.ports.email_port import EmailPort
from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.domain.constants import KST
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.services.issue_type_policy import is_license_issue_type
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)


def extract_tac_assigned_issues(
    widgets: Mapping[WidgetId, WidgetResult],
    keyword: str,
) -> list[RecentIssueDetail]:
    recent_result = widgets.get(WidgetId.RECENT_ISSUES)
    if recent_result is None:
        return []
    data = recent_result.data
    if not isinstance(data, RecentIssueWidgetData):
        return []
    return [
        detail
        for detail in data.issue_details
        if keyword in (detail.tac_team or "") and not is_license_issue_type(detail.type)
    ]


class NotifyTacAssignedUseCase:
    def __init__(
        self,
        email: EmailPort,
        notify_to: list[str],
        jira_base_url: str,
        renderer: IssueNotificationRendererPort,
        keyword: str = "\uc624\uacbd\uc11d",
    ) -> None:
        self._renderer = renderer
        self._email = email
        self._notify_to = notify_to
        self._jira_base_url = jira_base_url
        self._keyword = keyword
        self._notified_keys: set[str] = set()

    def _clear_missing(self, current_keys: set[str]) -> None:
        removed = self._notified_keys - current_keys
        if removed:
            logger.info(f"[NotifyTacAssigned] \uc13c\ud2f8\ub10c \uc81c\uac70: {removed}")
            self._notified_keys -= removed

    async def execute(self, widgets: Mapping[WidgetId, WidgetResult]) -> None:
        all_issues = extract_tac_assigned_issues(widgets, self._keyword)
        if not all_issues:
            return

        current_keys = {issue.key for issue in all_issues}
        self._clear_missing(current_keys)

        new_issues = [
            issue for issue in all_issues if issue.key not in self._notified_keys
        ]
        if not new_issues:
            logger.info(f"[NotifyTacAssigned] \uc2e0\uaddc \uc774\uc288 \uc5c6\uc74c (\uc774\ubbf8 \uc54c\ub9bc {len(self._notified_keys)}\uac74 \uc81c\uc678)")
            return

        for issue in new_issues:
            subject = f"[{issue.key}] TAC \ub2f4\ub2f9\uc790\ub85c \uc9c0\uc815\ub418\uc168\uc2b5\ub2c8\ub2e4."
            body = self._renderer.render_tac_assigned(issue, self._jira_base_url, datetime.now(KST))
            logger.info(f"[NotifyTacAssigned] {issue.key} \uba54\uc77c \ubc1c\uc1a1 \u2192 {self._notify_to}")
            await self._email.send(to=self._notify_to, subject=subject, body=body)

        self._notified_keys.update(issue.key for issue in new_issues)
