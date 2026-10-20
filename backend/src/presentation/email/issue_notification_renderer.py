# backend/src/presentation/email/issue_notification_renderer.py
from datetime import datetime
from html import escape
from urllib.parse import quote, urlsplit

from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.domain.entities.widget_data import RecentIssueDetail


def _render_todo(issues: list[RecentIssueDetail], jira_base_url: str, now: datetime) -> str:
    parsed_url = urlsplit(jira_base_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
        or "\\" in jira_base_url
        or any(character.isspace() or ord(character) < 32 for character in jira_base_url)
    ):
        raise ValueError("Jira base URL must be an HTTP(S) URL without credentials, whitespace, query or fragment")
    parsed_url.port
    base_url = jira_base_url.rstrip("/")
    now_str = now.strftime("%Y-%m-%d %H:%M")
    cell_style = "padding:14px 16px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top;line-height:1.6;"
    rows = []
    for issue in issues:
        summary = escape(issue.summary[:80])
        created = escape(issue.created[:16].replace("T", " "))
        url = escape(f"{base_url}/browse/{quote(issue.key, safe='')}", quote=True)
        rows.append(
            "<tr>"
            f"<td style=\"{cell_style}white-space:nowrap;\">"
            f"<a href=\"{url}\" style=\"color:#2563eb;text-decoration:none;font-weight:700;\">{escape(issue.key)}</a></td>"
            f"<td style=\"{cell_style}overflow-wrap:anywhere;\">{summary}</td>"
            f"<td style=\"{cell_style}white-space:nowrap;\">{escape(issue.type)}</td>"
            f"<td style=\"{cell_style}white-space:nowrap;color:#475569;\">{created}</td>"
            "</tr>"
        )
    headings = "".join(
        f"<th scope=\"col\" style=\"{cell_style}font-weight:600;color:#475569;\">{label}</th>"
        for label in ("이슈 번호", "요약", "유형", "생성일")
    )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"></head>"
        "<body style=\"margin:0;background:#f8fafc;color:#0f172a;font-family:Arial,'Malgun Gothic',sans-serif;\">"
        "<main style=\"padding:28px;max-width:1280px;margin:auto;\">"
        "<div style=\"font-size:12px;font-weight:700;letter-spacing:1px;color:#2563eb;\">TAC AUTO REPORTS</div>"
        "<h1 style=\"font-size:26px;margin:10px 0 12px;\">할 일 이슈 알림</h1>"
        f"<p style=\"margin:0;color:#475569;\">{now_str} KST 기준 · <strong>총 {len(issues)}건</strong></p>"
        "<p style=\"padding:14px 16px;margin:20px 0 24px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;font-size:14px;line-height:1.6;color:#1e40af;\">"
        "확인이 필요한 할 일 및 재오픈 이슈입니다. 티켓 번호를 누르면 Jira에서 상세 내용을 확인할 수 있습니다.</p>"
        "<section style=\"background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;\">"
        "<h2 style=\"font-size:17px;margin:0;padding:20px 16px;color:#0f172a;\">할 일 이슈 목록</h2>"
        "<table aria-label=\"할 일 이슈 목록\" style=\"border-collapse:collapse;width:100%;font-size:14px;background:#ffffff;\">"
        f"<thead style=\"background:#f1f5f9;\"><tr>{headings}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        "</section>"
        "<p style=\"margin-top:28px;color:#64748b;font-size:12px;\">TAC Auto Reports · 자동 알림</p>"
        "</main></body></html>"
    )


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
