# backend/src/application/use_cases/notify_todo_issues.py
import logging
from collections.abc import Mapping
from datetime import datetime

from src.application.ports.email_port import EmailPort
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


def _build_html(issues: list[RecentIssueDetail], jira_base_url: str) -> str:
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    rows = ""
    for issue in issues:
        summary = issue.summary[:80]
        created = issue.created[:16].replace("T", " ")
        url = f"{jira_base_url}/browse/{issue.key}"
        rows += (
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>"
            f"<a href='{url}' style='color:#2563eb;text-decoration:none;font-weight:bold;'>{issue.key}</a></td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{summary}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{issue.type}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{created}</td>"
            f"</tr>"
        )
    return f"""
<html><body style='font-family:sans-serif;color:#111;'>
<h2 style='color:#dc2626;'>&#9888; \ud560\uc77c \uc774\uc288 \uc54c\ub9bc</h2>
<p>\uae30\uc900 \uc2dc\uac01: <b>{now_str} KST</b> &nbsp;|&nbsp; \ucd1d <b>{len(issues)}</b>\uac74\uc758 \ud560\uc77c \uc774\uc288\uc774 \uc788\uc2b5\ub2c8\ub2e4.</p>
<table style='border-collapse:collapse;width:100%;font-size:14px;'>
  <thead>
    <tr style='background:#f3f4f6;'>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>\uc774\uc288 \ubc88\ud638</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>\uc694\uc57d</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>\uc720\ud615</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>\uc0dd\uc131\uc77c</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style='margin-top:20px;color:#6b7280;font-size:12px;'>TAC Auto Reports &mdash; \uc790\ub3d9 \uc54c\ub9bc</p>
</body></html>
"""


class NotifyTodoIssuesUseCase:
    def __init__(
        self,
        email: EmailPort,
        notify_to: list[str],
        jira_base_url: str,
    ) -> None:
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
        body = _build_html(new_issues, self._jira_base_url)
        excluded_str = str(self._notified_keys) if self._notified_keys else "없음"
        logger.info(f"[NotifyTodoIssues] 신규 {len(new_issues)}건 메일 발송 → {self._notify_to} (제외: {excluded_str})")
        await self._email.send(to=self._notify_to, subject=subject, body=body)

        self._notified_keys.update(issue.key for issue in new_issues)
