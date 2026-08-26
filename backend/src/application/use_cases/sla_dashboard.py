# backend/src/application/use_cases/sla_dashboard.py
import re
from html.parser import HTMLParser
from typing import Any

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraAttachmentContent, JiraPort
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.constants import JIRA_MAX_RESULT
from src.domain.entities.sla_dashboard import (
    SlaDashboardComment,
    SlaDashboardCommentImage,
    SlaDashboardIssue,
)
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId

_RECENT_COMMENT_LIMIT = 5
_ATTACHMENT_ID_PATTERN = re.compile(
    r"/(?:rest/api/[23]/attachment/content|secure/attachment)/(\d+)(?:[/?#]|$)",
    re.IGNORECASE,
)


class _CommentImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[SlaDashboardCommentImage] = []
        self._seen: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "img":
            return
        values = {name.lower(): value or "" for name, value in attrs}
        match = _ATTACHMENT_ID_PATTERN.search(values.get("src", ""))
        if match is None or match.group(1) in self._seen:
            return
        attachment_id = match.group(1)
        self._seen.add(attachment_id)
        self.images.append(
            SlaDashboardCommentImage(
                attachment_id=attachment_id,
                alt=values.get("alt") or values.get("title") or "댓글 첨부 이미지",
            )
        )


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


def _comment_images(value: object) -> tuple[SlaDashboardCommentImage, ...]:
    if not isinstance(value, str) or not value:
        return ()
    parser = _CommentImageParser()
    parser.feed(value)
    parser.close()
    return tuple(parser.images)


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
            fields="summary,issuetype,created,updated,status",
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
                    type=str(
                        (fields.get("issuetype") or {}).get("name") or detail.type
                    ),
                    summary=str(fields.get("summary") or detail.summary),
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

    async def get_comment_image(
        self,
        issue_key: str,
        comment_id: str,
        attachment_id: str,
    ) -> JiraAttachmentContent:
        comments = await self.list_recent_comments(issue_key)
        allowed = {
            image.attachment_id
            for comment in comments
            if comment.id == comment_id
            for image in comment.images
        }
        if attachment_id not in allowed:
            raise EntityNotFoundError("Comment image", attachment_id)
        return await self._jira.get_attachment_content(attachment_id)

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
            images=_comment_images(comment.get("renderedBody")),
        )
