# backend/src/domain/ports/jira_port.py
from abc import ABC, abstractmethod
from typing import Any


class JiraPort(ABC):
    @abstractmethod
    def get_issue_count(self, jql: str) -> int: ...

    @abstractmethod
    def get_issues(
        self,
        jql: str,
        max_results: int = 200,
        fields: str = "",
    ) -> list[dict[str, Any]]: ...
