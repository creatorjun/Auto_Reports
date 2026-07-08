# backend/src/application/widgets/created_vs_resolved_collector.py
import asyncio
import logging

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    CreatedResolvedIssueDetail,
    CreatedVsResolvedWidgetData,
    ResolvedIssueDetail,
)
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class CreatedVsResolvedCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[CreatedVsResolvedWidgetData]:
        created_jql, resolved_jql = self._q.w14_created_vs_resolved()

        created_count, resolved_count, created_issues, resolved_issues = await asyncio.gather(
            self._jira.get_issue_count(created_jql),
            self._jira.get_issue_count(resolved_jql),
            self._jira.get_issues(created_jql, max_results=200, fields="summary,issuetype,status,created"),
            self._jira.get_issues(resolved_jql, max_results=200, fields="summary,issuetype,resolutiondate"),
        )

        created_details: list[CreatedResolvedIssueDetail] = []
        for issue in created_issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            created_details.append(
                CreatedResolvedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    created=(fields.get("created") or "")[:16].replace("T", " "),
                )
            )
        created_details.sort(key=lambda item: item.created, reverse=True)

        resolved_details: list[ResolvedIssueDetail] = []
        for issue in resolved_issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            resolved = fields.get("resolutiondate") or ""
            resolved_details.append(
                ResolvedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    resolved=resolved[:16].replace("T", " "),
                )
            )
        resolved_details.sort(key=lambda item: item.resolved, reverse=True)

        logger.info(f"[W14] 생성 {created_count}건 / 해결 {resolved_count}건")
        return WidgetResult(
            name="생성 vs 해결",
            total=created_count + resolved_count,
            data=CreatedVsResolvedWidgetData(
                created=created_count,
                resolved=resolved_count,
                created_details=created_details,
                resolved_details=resolved_details,
            ),
        )
