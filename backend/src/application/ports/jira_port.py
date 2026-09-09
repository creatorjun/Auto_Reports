# backend/src/application/ports/jira_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class JiraIssueField(StrEnum):
    SUMMARY = "summary"
    ISSUE_TYPE = "issue_type"
    STATUS = "status"
    CREATED = "created"
    UPDATED = "updated"
    RESOLVED = "resolved"
    PRIORITY = "priority"
    REPORTER = "reporter"
    ASSIGNEE = "assignee"


@dataclass(frozen=True)
class JiraAssetReference:
    workspace_id: str
    object_id: str


@dataclass(frozen=True)
class JiraIssue:
    key: str = ""
    summary: str = ""
    issue_type: str = ""
    status: str = ""
    created: str = ""
    updated: str = ""
    resolved: str = ""
    priority: str = ""
    reporter: str = ""
    assignee: str = ""
    tac_assignee: str = ""
    qa_assignee: str = ""
    recent_tac_assignee: str = ""
    initial_response_breached: bool = False
    resolution_breached: bool = False
    redeployment_month: str = ""
    redeployment_cause: str = ""
    partner_references: tuple[JiraAssetReference, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JiraCommentImage:
    attachment_id: str
    alt: str


@dataclass(frozen=True)
class JiraComment:
    id: str
    author: str
    body: str
    created: str
    updated: str
    images: tuple[JiraCommentImage, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JiraAttachmentContent:
    data: bytes
    media_type: str


class JiraPort(ABC):
    MAX_RESULTS: int = 100

    @abstractmethod
    async def get_project_issue_types(self, project_key: str) -> list[str]: ...

    @abstractmethod
    async def get_issue_count(self, jql: str) -> int: ...

    @abstractmethod
    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]: ...

    @abstractmethod
    async def get_issues(
        self,
        jql: str,
        max_results: int | None = MAX_RESULTS,
        fields: frozenset[JiraIssueField] = frozenset(),
    ) -> list[JiraIssue]: ...

    @abstractmethod
    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int | None = MAX_RESULTS,
    ) -> list[JiraIssue]: ...

    @abstractmethod
    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int | None = MAX_RESULTS,
    ) -> list[JiraIssue]: ...

    @abstractmethod
    async def get_redeployment_issues(
        self,
        jql: str,
        max_results: int | None = MAX_RESULTS,
    ) -> list[JiraIssue]: ...

    @abstractmethod
    async def get_issue_comments(
        self,
        issue_key: str,
        max_results: int = 5,
        offset: int = 0,
    ) -> list[JiraComment]: ...

    @abstractmethod
    async def get_issue_comment(
        self,
        issue_key: str,
        comment_id: str,
    ) -> JiraComment | None: ...

    @abstractmethod
    async def get_attachment_content(
        self,
        attachment_id: str,
    ) -> JiraAttachmentContent: ...

    @abstractmethod
    async def get_asset_object_labels(
        self,
        references: list[JiraAssetReference],
    ) -> dict[JiraAssetReference, str]: ...

    @abstractmethod
    async def aclose(self) -> None: ...
