# backend/src/application/ports/jira_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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
        fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int = MAX_RESULTS,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int = MAX_RESULTS,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_issue_comments(
        self,
        issue_key: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_attachment_content(
        self,
        attachment_id: str,
    ) -> JiraAttachmentContent: ...

    @abstractmethod
    async def get_sla_field_ids(self) -> dict[str, str]: ...

    @abstractmethod
    async def get_asset_object_labels(
        self,
        references: list[tuple[str, str]],
    ) -> dict[tuple[str, str], str]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def aclose(self) -> None: ...
