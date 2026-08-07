# backend/src/application/use_cases/notify_todo_issues.py
import logging
from datetime import datetime

from src.domain.ports.email_port import EmailPort
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULT, KST

logger = logging.getLogger(__name__)

_TODO_STATUS = "할 일"
_REOPEN_STATUS = "재오픈"
_TODO_STATUSES = {_TODO_STATUS, _REOPEN_STATUS}


def _build_html(issues: list[dict], jira_base_url: str) -> str:
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    rows = ""
    for issue in issues:
        fields = issue.get("fields") or {}
        key = issue.get("key", "")
        summary = (fields.get("summary") or "")[:80]
        status = (fields.get("status") or {}).get("name", "")
        issue_type = (fields.get("issuetype") or {}).get("name", "")
        created = (fields.get("created") or "")[:16].replace("T", " ")
        url = f"{jira_base_url}/browse/{key}"
        rows += (
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>"
            f"<a href='{url}' style='color:#2563eb;text-decoration:none;'>{key}</a></td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{summary}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{issue_type}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{status}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #e5e7eb;'>{created}</td>"
            f"</tr>"
        )
    return f"""
<html><body style='font-family:sans-serif;color:#111;'>
<h2 style='color:#dc2626;'>&#9888; 할일 이슈 알림</h2>
<p>기준 시각: <b>{now_str} KST</b> &nbsp;|&nbsp; 총 <b>{len(issues)}</b>건의 미처리 이슈가 있습니다.</p>
<table style='border-collapse:collapse;width:100%;font-size:14px;'>
  <thead>
    <tr style='background:#f3f4f6;'>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>이슈 번호</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>요약</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>유형</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>상태</th>
      <th style='padding:8px 12px;text-align:left;border-bottom:2px solid #d1d5db;'>생성일</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style='margin-top:20px;color:#6b7280;font-size:12px;'>TAC Auto Reports &mdash; 자동 알림</p>
</body></html>
"""


class NotifyTodoIssuesUseCase:
    def __init__(
        self,
        jira: JiraPort,
        email: EmailPort,
        project_key: str,
        issue_types: list[str],
        closed_statuses: list[str],
        notify_to: list[str],
        jira_base_url: str,
    ) -> None:
        self._jira = jira
        self._email = email
        self._project_key = project_key
        self._issue_types = issue_types
        self._closed_statuses = closed_statuses
        self._notify_to = notify_to
        self._jira_base_url = jira_base_url

    def _build_jql(self) -> str:
        types = ", ".join(
            f'"{t}"' if " " in t else t for t in self._issue_types
        )
        closed = ", ".join(f'"{s}"' for s in self._closed_statuses)
        todo = ", ".join(f'"{s}"' for s in sorted(_TODO_STATUSES))
        return (
            f"project = {self._project_key} AND issuetype IN ({types}) "
            f"AND status IN ({todo}) "
            f"AND status NOT IN ({closed}) "
            f"ORDER BY issuekey DESC"
        )

    async def execute(self) -> None:
        jql = self._build_jql()
        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULT
        )
        todo_issues = [
            i for i in issues
            if ((i.get("fields") or {}).get("status") or {}).get("name", "") in _TODO_STATUSES
        ]
        if not todo_issues:
            logger.info("[NotifyTodoIssues] 할일 이슈 없음 — 메일 발송 생략")
            return

        logger.info(f"[NotifyTodoIssues] 할일 이슈 {len(todo_issues)}건 — 메일 발송")
        subject = f"[TAC] 미처리 할일 이슈 {len(todo_issues)}건 알림"
        body = _build_html(todo_issues, self._jira_base_url)
        await self._email.send(to=self._notify_to, subject=subject, body=body)
