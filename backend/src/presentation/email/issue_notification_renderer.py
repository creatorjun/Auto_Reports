# backend/src/presentation/email/issue_notification_renderer.py
from datetime import datetime

from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.domain.entities.widget_data import RecentIssueDetail


def _render_todo(issues: list[RecentIssueDetail], jira_base_url: str, now: datetime) -> str:
    now_str = now.strftime("%Y-%m-%d %H:%M")
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


def _render_tac_assigned(issue: RecentIssueDetail, jira_base_url: str, now: datetime) -> str:
    summary = issue.summary[:100]
    created = issue.created[:16].replace("T", " ")
    url = f"{jira_base_url}/browse/{issue.key}"
    now_str = now.strftime("%Y-%m-%d %H:%M")
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


class IssueNotificationRenderer(IssueNotificationRendererPort):
    def render_todo(
        self, issues: list[RecentIssueDetail], jira_base_url: str, now: datetime,
    ) -> str:
        return _render_todo(issues, jira_base_url, now)

    def render_tac_assigned(
        self, issue: RecentIssueDetail, jira_base_url: str, now: datetime,
    ) -> str:
        return _render_tac_assigned(issue, jira_base_url, now)
