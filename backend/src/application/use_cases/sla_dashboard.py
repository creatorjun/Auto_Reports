# backend/src/application/use_cases/sla_dashboard.py
import re

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import (
    JiraAttachmentContent,
    JiraComment,
    JiraIssueField,
    JiraPort,
)
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.constants import JIRA_MAX_RESULT
from src.domain.entities.sla_dashboard import (
    SlaDashboardComment,
    SlaDashboardCommentImage,
    SlaDashboardCommentPage,
    SlaDashboardIssue,
)
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId

_RECENT_COMMENT_LIMIT = 5


def _format_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:16].replace("T", " ")


class SlaDashboardUseCase:
    def __init__(
        self,
        reports: GetReportUseCase,
        jira: JiraPort,
        project_key: str,
    ) -> None:
        self._reports = reports
        self._jira = jira
        self._issue_key_pattern = re.compile(
            rf"{re.escape(project_key.upper())}-\d+"
        )

    async def list_recent_issues(self) -> list[SlaDashboardIssue]:
        details = await self._recent_issue_details()
        keys = [
            detail.key.upper()
            for detail in details
            if self._is_valid_key(detail.key)
        ]
        if not keys:
            return []

        jql = f"issuekey IN ({', '.join(keys)}) ORDER BY created ASC, issuekey ASC"
        issues = await self._jira.get_issues(
            jql,
            max_results=JIRA_MAX_RESULT,
            fields=frozenset({
                JiraIssueField.SUMMARY,
                JiraIssueField.ISSUE_TYPE,
                JiraIssueField.CREATED,
                JiraIssueField.UPDATED,
                JiraIssueField.STATUS,
            }),
        )
        live_by_key = {
            issue.key.upper(): issue
            for issue in issues
            if issue.key
        }

        result: list[SlaDashboardIssue] = []
        for detail in details:
            key = detail.key.upper()
            if not self._is_valid_key(key):
                continue
            live = live_by_key.get(key)
            result.append(
                SlaDashboardIssue(
                    key=key,
                    type=(live.issue_type if live else "") or detail.type,
                    summary=(live.summary if live else "") or detail.summary,
                    created=_format_timestamp(live.created if live else "") or detail.created,
                    updated=_format_timestamp(live.updated if live else ""),
                    status=(live.status if live else "") or detail.status,
                )
            )
        return sorted(
            result,
            key=lambda issue: (not issue.created, issue.created, issue.key),
        )

    async def list_recent_comments(
        self,
        issue_key: str,
        offset: int = 0,
        limit: int = _RECENT_COMMENT_LIMIT,
    ) -> SlaDashboardCommentPage:
        if offset < 0:
            raise ValueError("Comment offset must be nonnegative")
        if limit < 1:
            raise ValueError("Comment limit must be positive")
        normalized_key = await self._require_recent_issue(issue_key)
        comments = await self._jira.get_issue_comments(
            normalized_key,
            max_results=limit + 1,
            offset=offset,
        )
        return SlaDashboardCommentPage(
            comments=tuple(
                self._to_comment(comment)
                for comment in comments[:limit]
            ),
            next_offset=(
                offset + limit
                if len(comments) > limit
                else None
            ),
        )

    async def get_comment_image(
        self,
        issue_key: str,
        comment_id: str,
        attachment_id: str,
    ) -> JiraAttachmentContent:
        normalized_key = await self._require_recent_issue(issue_key)
        if not comment_id.isdigit():
            raise EntityNotFoundError("Comment", comment_id)
        comment = await self._jira.get_issue_comment(normalized_key, comment_id)
        if comment is None or comment.id != comment_id:
            raise EntityNotFoundError("Comment", comment_id)
        allowed = {
            image.attachment_id
            for image in comment.images
        }
        if attachment_id not in allowed:
            raise EntityNotFoundError("Comment image", attachment_id)
        return await self._jira.get_attachment_content(attachment_id)

    async def _require_recent_issue(self, issue_key: str) -> str:
        normalized_key = issue_key.upper()
        details = await self._recent_issue_details()
        recent_keys = {
            detail.key.upper()
            for detail in details
            if self._is_valid_key(detail.key)
        }
        if not self._is_valid_key(normalized_key) or normalized_key not in recent_keys:
            raise EntityNotFoundError("Recent issue", issue_key)
        return normalized_key

    async def _recent_issue_details(self) -> list[RecentIssueDetail]:
        report = await self._reports.get_latest()
        if report is None:
            return []
        widget = report.widgets.get(WidgetId.RECENT_ISSUES)
        if widget is None or not isinstance(widget.data, RecentIssueWidgetData):
            return []
        return widget.data.issue_details

    def _is_valid_key(self, issue_key: str) -> bool:
        return self._issue_key_pattern.fullmatch(issue_key.upper()) is not None

    @staticmethod
    def _to_comment(comment: JiraComment) -> SlaDashboardComment:
        return SlaDashboardComment(
            id=comment.id,
            author=comment.author,
            body=comment.body,
            created=_format_timestamp(comment.created),
            updated=_format_timestamp(comment.updated),
            images=tuple(
                SlaDashboardCommentImage(
                    attachment_id=image.attachment_id,
                    alt=image.alt,
                )
                for image in comment.images
            ),
        )
