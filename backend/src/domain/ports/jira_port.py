# backend/src/domain/ports/jira_port.py
from abc import ABC, abstractmethod
from typing import Any


class JiraPort(ABC):
    @abstractmethod
    async def get_issue_count(self, jql: str) -> int: ...

    @abstractmethod
    async def get_issues(
        self,
        jql: str,
        max_results: int = 200,
        fields: str = "",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_sla_field_ids(self) -> dict[str, str]:
        """이름 → customfield_id 매핑 반환.
        예) {'시간 안에 첫 응답': 'customfield_10020', '해결 시간': 'customfield_10030'}
        """
        ...

    @abstractmethod
    async def aclose(self) -> None: ...
