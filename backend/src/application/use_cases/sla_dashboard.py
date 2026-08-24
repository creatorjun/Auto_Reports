# backend/src/application/use_cases/sla_dashboard.py
import re
from typing import Any

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraPort
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.constants import JIRA_MAX_RESULT
from src.domain.entities.sla_dashboard import SlaDashboardComment, SlaDashboardIssue
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId

_RECENT_COMMENT_LIMIT = 5


def _format_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:16].replace("T", " ")


def _adf_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_adf_text(item) for item in value)
    if not isinstance(value, dict):
        return ""

    node_type = value.get("type", "")
    attrs = value.get("attrs") or {}
    if node_type == "text":
        return str(value.get("text", ""))
    if node_type == "hardBreak":
        return "\n"
    if node_type == "mention":
        return str(attrs.get("text") or attrs.get("displayName") or "")
    if node_type == "emoji":
        return str(attrs.get("text") or attrs.get("shortName") or "")

    content = _adf_text(value.get("content") or [])
    if node_type == "listItem":
        return f"- {content.strip()}\n"
    if node_type in {"paragraph", "heading", "blockquote", "codeBlock"}:
        return f"{content.rstrip()}\n"
    return content


def _comment_body(value: object) -> str:
    return _adf_text(value).strip()


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
            fields="created,updated,status",
        )
        live_by_key = {
            str(issue.get("key", "")).upper(): issue
            for issue in issues
            if issue.get("key")
        }

        result: list[SlaDashboardIssue] = []
        for detail in details:
            key = detail.key.upper()
            if not self._is_valid_key(key):
                continue
            fields = (live_by_key.get(key) or {}).get("fields") or {}
            status = (fields.get("status") or {}).get("name") or detail.status
            result.append(
                SlaDashboardIssue(
                    key=key,
                    created=(
                        _format_timestamp(fields.get("created")) or detail.created
                    ),
                    updated=_format_timestamp(fields.get("updated")),
                    status=status,
                )
            )
        return sorted(
            result,
            key=lambda issue: (not issue.created, issue.created, issue.key),
        )

    async def list_recent_comments(self, issue_key: str) -> list[SlaDashboardComment]:
        normalized_key = issue_key.upper()
        details = await self._recent_issue_details()
        recent_keys = {
            detail.key.upper()
            for detail in details
            if self._is_valid_key(detail.key)
        }
        if not self._is_valid_key(normalized_key) or normalized_key not in recent_keys:
            raise EntityNotFoundError("Recent issue", issue_key)

        comments = await self._jira.get_issue_comments(
            normalized_key,
            max_results=_RECENT_COMMENT_LIMIT,
        )
        ordered = sorted(
            comments,
            key=lambda comment: str(comment.get("created", "")),
            reverse=True,
        )[:_RECENT_COMMENT_LIMIT]
        return [self._to_comment(comment) for comment in ordered]

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
    def _to_comment(comment: dict[str, Any]) -> SlaDashboardComment:
        author = comment.get("author") or {}
        return SlaDashboardComment(
            id=str(comment.get("id", "")),
            author=str(
                author.get("displayName") or author.get("name") or "알 수 없음"
            ),
            body=_comment_body(comment.get("body")),
            created=_format_timestamp(comment.get("created")),
            updated=_format_timestamp(comment.get("updated")),
        )
