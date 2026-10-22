# backend/src/application/use_cases/issue_management.py
import asyncio
import logging
import math
import re
from dataclasses import replace
from datetime import date, datetime
from time import monotonic

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraAttachmentContent
from src.application.ports.jira_port import JiraIssue, JiraIssueField, JiraPort
from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot, IssueManagementSnapshotPort
from src.application.services.issue_age import issue_created_display, issue_elapsed_days
from src.application.services.issue_details import IssueDetailsService
from src.domain.constants import KST, STAGE_MAP
from src.domain.entities.sla_dashboard import SlaDashboardCommentPage, SlaDashboardDescription
from src.domain.entities.widget_data import RecentIssueDetail

logger = logging.getLogger(__name__)


class IssueManagementUseCase:
    def __init__(self, jira: JiraPort, project_key: str = "TACEA", snapshots: IssueManagementSnapshotPort | None = None) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        self._jira = jira
        self._project_key = project_key
        self._issue_key_pattern = re.compile(rf"{re.escape(project_key.upper())}-\d+")
        self._issue_details = IssueDetailsService(jira)
        self._snapshots = snapshots
        self._snapshot_loaded = snapshots is None
        self._restore_lock = asyncio.Lock()
        self._issues: dict[str, RecentIssueDetail] = {}
        self._details: tuple[RecentIssueDetail, ...] = ()
        self._details_date: date | None = None
        self._initialized = False
        self._last_sync = 0.0
        self._last_full_sync = 0.0
        self._last_attempt = float("-inf")
        self._synced_at: str | None = None
        self._full_synced_at: datetime | None = None
        self._error: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        async with self._restore_lock:
            if self._snapshot_loaded:
                return
            try:
                snapshot = await self._snapshots.load(self._project_key)
                if snapshot is not None:
                    self._accept_snapshot(snapshot)
                self._snapshot_loaded = True
            except Exception as error:
                logger.warning("Issue snapshot restore failed (%s)", type(error).__name__)

    def _accept_snapshot(self, snapshot: IssueManagementSnapshot) -> None:
        now = datetime.now(KST)
        tick = monotonic()
        self._issues = {issue.key: replace(issue) for issue in snapshot.issues}
        self._details_date = None
        self._initialized = True
        self._last_sync = tick - max(0, (now - snapshot.synced_at).total_seconds())
        self._last_full_sync = tick - max(0, (now - snapshot.full_synced_at).total_seconds())
        if snapshot.synced_at > now:
            self._last_full_sync = float("-inf")
        self._synced_at = snapshot.synced_at.isoformat()
        self._full_synced_at = snapshot.full_synced_at
        self._error = None

    @staticmethod
    def _issue_detail(issue: JiraIssue) -> RecentIssueDetail:
        team, team_account_id = next(((name, account_id) for name, account_id in (
            (issue.tac_assignee, issue.tac_assignee_account_id),
            (issue.qa_assignee, issue.qa_assignee_account_id),
            (issue.assignee, issue.assignee_account_id),
        ) if name), ("미지정", None))
        return RecentIssueDetail(
            key=issue.key, summary=issue.summary, type=issue.issue_type or "기타",
            status=issue.status or "기타", stage_index=STAGE_MAP.get(issue.status, 99),
            created=issue.created, elapsed_days=0, reporter=issue.reporter or "미지정",
            tac_team=team, tac_assignee=issue.recent_tac_assignee or "미지정",
            reporter_account_id=issue.reporter_account_id, tac_team_account_id=team_account_id,
            tac_assignee_account_id=issue.recent_tac_assignee_account_id,
            personal_data_retrieved_at=issue.personal_data_retrieved_at,
        )

    async def list_issues(self) -> dict:
        await self.initialize()
        if (self._task is None or self._task.done()) and monotonic() - self._last_attempt >= 30:
            self._last_attempt = monotonic()
            self._task = asyncio.create_task(self._refresh())
        now = datetime.now(KST)
        if self._details_date != now.date():
            self._details = tuple(replace(issue,
                created=issue_created_display(issue.created),
                elapsed_days=issue_elapsed_days(issue.created, now),
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
        started_at = datetime.now(KST)
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
            incoming = {issue.key: self._issue_detail(issue) for issue in page.issues}
            snapshot = IssueManagementSnapshot(
                issues=tuple((incoming if full else {**self._issues, **incoming}).values()),
                synced_at=started_at,
                full_synced_at=started_at if full else self._full_synced_at or started_at,
            )
            if self._snapshots is not None:
                snapshot = await self._snapshots.save(self._project_key, snapshot)
            self._accept_snapshot(snapshot)
            self._snapshot_loaded = True
        except Exception as error:
            logger.warning("Issue synchronization failed (%s)", type(error).__name__)
            self._error = "Jira 동기화에 실패했습니다. 기존 캐시를 유지하며 자동 재시도합니다."

    async def require_issue_key(self, issue_key: str) -> str:
        normalized_key = issue_key.upper()
        if self._issue_key_pattern.fullmatch(normalized_key) is None:
            raise EntityNotFoundError("Issue", issue_key)
        await self.initialize()
        if normalized_key not in self._issues:
            raise EntityNotFoundError("Issue", issue_key)
        return normalized_key

    async def get_issue_description(self, issue_key: str) -> SlaDashboardDescription:
        key = await self.require_issue_key(issue_key)
        return await self._issue_details.get_description(key)

    async def get_description_image(self, issue_key: str, attachment_id: str) -> JiraAttachmentContent:
        key = await self.require_issue_key(issue_key)
        return await self._issue_details.get_description_image(key, attachment_id)

    async def list_recent_comments(self, issue_key: str, offset: int = 0, limit: int = 5) -> SlaDashboardCommentPage:
        if offset < 0:
            raise ValueError("Comment offset must be nonnegative")
        if limit < 1:
            raise ValueError("Comment limit must be positive")
        key = await self.require_issue_key(issue_key)
        return await self._issue_details.get_comments(key, offset, limit)

    async def get_comment_image(self, issue_key: str, comment_id: str, attachment_id: str) -> JiraAttachmentContent:
        key = await self.require_issue_key(issue_key)
        return await self._issue_details.get_comment_image(key, comment_id, attachment_id)

    async def aclose(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def clear_personal_data_cache(self) -> None:
        async with self._restore_lock:
            await self.aclose()
            self._task = None
            self._issues.clear()
            self._details = ()
            self._details_date = None
            self._initialized = False
            self._snapshot_loaded = self._snapshots is None
            self._last_sync = 0.0
            self._last_full_sync = 0.0
            self._last_attempt = float("-inf")
            self._synced_at = None
            self._full_synced_at = None
            self._error = None
