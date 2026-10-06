# backend/src/application/use_cases/issue_management.py
import asyncio
import math
import re
from dataclasses import replace
from datetime import date, datetime
from time import monotonic

from src.application.ports.jira_port import JiraIssue, JiraIssueField, JiraPort
from src.application.services.issue_age import issue_created_display, issue_elapsed_days
from src.domain.constants import KST, STAGE_MAP
from src.domain.entities.widget_data import RecentIssueDetail


class IssueManagementUseCase:
    def __init__(self, jira: JiraPort, project_key: str = "TACEA") -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        self._jira = jira
        self._project_key = project_key
        self._issues: dict[str, JiraIssue] = {}
        self._details: tuple[RecentIssueDetail, ...] = ()
        self._details_date: date | None = None
        self._initialized = False
        self._last_sync = 0.0
        self._last_full_sync = 0.0
        self._last_attempt = float("-inf")
        self._synced_at: str | None = None
        self._error: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def list_issues(self) -> dict:
        if (self._task is None or self._task.done()) and monotonic() - self._last_attempt >= 30:
            self._last_attempt = monotonic()
            self._task = asyncio.create_task(self._refresh())
        now = datetime.now(KST)
        if self._details_date != now.date():
            self._details = tuple(RecentIssueDetail(
                key=issue.key,
                summary=issue.summary,
                type=issue.issue_type or "기타",
                status=issue.status or "기타",
                stage_index=STAGE_MAP.get(issue.status, 99),
                created=issue_created_display(issue.created),
                elapsed_days=issue_elapsed_days(issue.created, now),
                reporter=issue.reporter or "미지정",
                tac_team=issue.tac_assignee or issue.qa_assignee or issue.assignee or "미지정",
                tac_assignee=issue.recent_tac_assignee or "미지정",
            ) for issue in sorted(self._issues.values(), key=lambda item: (item.created, item.key), reverse=True))
            self._details_date = now.date()
        return {
            "issues": [replace(issue) for issue in self._details],
            "initialized": self._initialized,
            "refreshing": self._task is not None and not self._task.done(),
            "synced_at": self._synced_at,
            "error": self._error,
        }

    async def _refresh(self) -> None:
        started = monotonic()
        started_at = datetime.now(KST).isoformat()
        full = not self._initialized or started - self._last_full_sync >= 3600
        jql = f'project = "{self._project_key}"'
        if not full:
            minutes = math.ceil((started - self._last_sync) / 60) + 2
            jql += f' AND updated >= "-{minutes}m"'
        jql += " ORDER BY created DESC, key DESC"
        try:
            page = await self._jira.get_report_chart_issues(
                jql, None, frozenset(JiraIssueField),
            )
            if page.has_more or any(not issue.key for issue in page.issues):
                raise RuntimeError("Incomplete Jira snapshot")
            incoming = {issue.key: issue for issue in page.issues}
            self._issues = incoming if full else {**self._issues, **incoming}
            self._details_date = None
            self._initialized = True
            self._last_sync = started
            if full:
                self._last_full_sync = started
            self._synced_at = started_at
            self._error = None
        except Exception:
            self._error = "Jira 동기화에 실패했습니다. 기존 캐시를 유지하며 자동 재시도합니다."

    async def aclose(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
