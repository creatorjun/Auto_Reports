# backend/src/domain/ports/jira_port.py
from abc import ABC, abstractmethod
from typing import Any

from src.shared.constants import JIRA_MAX_RESULTS_DEFAULT


class JiraPort(ABC):
    @abstractmethod
    async def get_issue_count(self, jql: str) -> int: ...

    @abstractmethod
    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]: ...

    @abstractmethod
    async def get_issues(
        self,
        jql: str,
        max_results: int = JIRA_MAX_RESULTS_DEFAULT,
        fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int = 500,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int = 200,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_sla_field_ids(self) -> dict[str, str]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def aclose(self) -> None: ...
