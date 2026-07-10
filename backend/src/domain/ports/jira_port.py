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
    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int = 500,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]:
        """SLA customfield 값이 포함된 이슈 목록을 반환한다.
        반환된 각 issue['fields']에는 '_sla_initial' 과 '_sla_resolution' 키로
        최초응답 / 해결시간 SLA 값이 정규화되어 포함된다.
        """
        ...

    @abstractmethod
    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int = 200,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]:
        """TAC/QA 담당자 customfield 값이 포함된 이슈 목록을 반환한다.
        반환된 각 issue['fields']에는 '_tac_assignee', '_qa_assignee' 키가 포함된다.
        """
        ...

    @abstractmethod
    async def get_sla_field_ids(self) -> dict[str, str]:
        """이름 -> customfield_id 매핑 반환.
        예) {'시간 안에 첫 응답': 'customfield_10020', '해결 시간': 'customfield_10030'}
        """
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """JIRA 이슈 텍스트 검색. 상위 limit개 결과 반환."""
        ...

    @abstractmethod
    async def aclose(self) -> None: ...
