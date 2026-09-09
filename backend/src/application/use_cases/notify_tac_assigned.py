# backend/src/application/use_cases/notify_tac_assigned.py
import logging
from collections.abc import Mapping
from datetime import datetime

from src.application.ports.email_port import EmailPort
from src.domain.constants import KST
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
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
        if keyword in (detail.tac_team or "")
    ]


def _build_html(issue: RecentIssueDetail, jira_base_url: str) -> str:
    summary = issue.summary[:100]
    created = issue.created[:16].replace("T", " ")
    url = f"{jira_base_url}/browse/{issue.key}"
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    return f"""
<html><body style='font-family:sans-serif;color:#111;'>
<h2 style='color:#2563eb;'>&#128203; TAC \ub2f4\ub2f9\uc790\ub85c \uc9c0\uc815\ub418\uc168\uc2b5\ub2c8\ub2e4</h2>
<p>\uae30\uc900 \uc2dc\uac01: <b>{now_str} KST</b></p>
<table style='border-collapse:collapse;width:100%;font-size:14px;margin-top:12px;'>
  <tr style='background:#f3f4f6;'>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;width:120px;'>\uc774\uc288 \ubc88\ud638</td>
    <td style='padding:8px 14px;'><a href='{url}' style='color:#2563eb;font-weight:bold;text-decoration:none;'>{issue.key}</a></td>
  </tr>
  <tr>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;'>\uc81c\ubaa9</td>
    <td style='padding:8px 14px;'>{summary}</td>
  </tr>
  <tr style='background:#f3f4f6;'>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;'>\uc720\ud615</td>
    <td style='padding:8px 14px;'>{issue.type}</td>
  </tr>
  <tr>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;'>\uc0c1\ud0dc</td>
    <td style='padding:8px 14px;'>{issue.status}</td>
  </tr>
  <tr style='background:#f3f4f6;'>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;'>TAC \ub2f4\ub2f9\uc790</td>
    <td style='padding:8px 14px;'>{issue.tac_team}</td>
  </tr>
  <tr>
    <td style='padding:8px 14px;color:#6b7280;font-weight:bold;'>\uc0dd\uc131\uc77c</td>
    <td style='padding:8px 14px;'>{created}</td>
  </tr>
</table>
<p style='margin-top:20px;'>
  <a href='{url}' style='background:#2563eb;color:#fff;padding:10px 20px;text-decoration:none;border-radius:6px;font-size:14px;'>\ud2f0\ucf13 \uc5f4\uae30</a>
</p>
<p style='margin-top:24px;color:#6b7280;font-size:12px;'>TAC Auto Reports &mdash; \uc790\ub3d9 \uc54c\ub9bc</p>
</body></html>
"""


class NotifyTacAssignedUseCase:
    def __init__(
        self,
        email: EmailPort,
        notify_to: list[str],
        jira_base_url: str,
        keyword: str = "\uc624\uacbd\uc11d",
    ) -> None:
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
            body = _build_html(issue, self._jira_base_url)
            logger.info(f"[NotifyTacAssigned] {issue.key} \uba54\uc77c \ubc1c\uc1a1 \u2192 {self._notify_to}")
            await self._email.send(to=self._notify_to, subject=subject, body=body)

        self._notified_keys.update(issue.key for issue in new_issues)
