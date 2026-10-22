# backend/src/application/services/issue_details.py
from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraAttachmentContent, JiraComment, JiraPort
from src.domain.entities.sla_dashboard import (
    SlaDashboardComment,
    SlaDashboardCommentImage,
    SlaDashboardCommentPage,
    SlaDashboardDescription,
)


def format_issue_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:16].replace("T", " ")


class IssueDetailsService:
    def __init__(self, jira: JiraPort) -> None:
        self._jira = jira

    async def get_description(self, issue_key: str) -> SlaDashboardDescription:
        description = await self._jira.get_issue_description(issue_key)
        if description is None:
            raise EntityNotFoundError("Issue description", issue_key)
        return SlaDashboardDescription(
            body=description.body,
            images=tuple(SlaDashboardCommentImage(image.attachment_id, image.alt) for image in description.images),
        )

    async def get_description_image(self, issue_key: str, attachment_id: str) -> JiraAttachmentContent:
        description = await self.get_description(issue_key)
        if not attachment_id.isdigit() or attachment_id not in {image.attachment_id for image in description.images}:
            raise EntityNotFoundError("Description image", attachment_id)
        return await self._jira.get_attachment_content(attachment_id)

    async def get_comments(self, issue_key: str, offset: int = 0, limit: int = 5) -> SlaDashboardCommentPage:
        if offset < 0:
            raise ValueError("Comment offset must be nonnegative")
        if limit < 1:
            raise ValueError("Comment limit must be positive")
        comments = await self._jira.get_issue_comments(issue_key, max_results=limit + 1, offset=offset)
        return SlaDashboardCommentPage(
            comments=tuple(self._to_comment(comment) for comment in comments[:limit]),
            next_offset=offset + limit if len(comments) > limit else None,
        )

    async def get_comment_image(self, issue_key: str, comment_id: str, attachment_id: str) -> JiraAttachmentContent:
        if not comment_id.isdigit():
            raise EntityNotFoundError("Comment", comment_id)
        comment = await self._jira.get_issue_comment(issue_key, comment_id)
        if comment is None or comment.id != comment_id:
            raise EntityNotFoundError("Comment", comment_id)
        if attachment_id not in {image.attachment_id for image in comment.images}:
            raise EntityNotFoundError("Comment image", attachment_id)
        return await self._jira.get_attachment_content(attachment_id)

    @staticmethod
    def _to_comment(comment: JiraComment) -> SlaDashboardComment:
        return SlaDashboardComment(
            id=comment.id,
            author=comment.author,
            body=comment.body,
            created=format_issue_timestamp(comment.created),
            updated=format_issue_timestamp(comment.updated),
            images=tuple(SlaDashboardCommentImage(image.attachment_id, image.alt) for image in comment.images),
        )
