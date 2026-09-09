# backend/src/application/widgets/created_vs_resolved_collector.py
import asyncio
import logging

from src.application.ports.jira_port import JiraIssue, JiraIssueField, JiraPort
from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    CreatedVsResolvedWidgetData,
    CreatedResolvedIssueDetail,
    ResolvedIssueDetail,
)
logger = logging.getLogger(__name__)


class CreatedVsResolvedCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[CreatedVsResolvedWidgetData]:
        created_jql, resolved_jql = self._q.w3_created_vs_resolved()
        created_issues, resolved_issues = await asyncio.gather(
            self._jira.get_issues(
                created_jql, max_results=None,
                fields=frozenset({
                    JiraIssueField.SUMMARY,
                    JiraIssueField.ISSUE_TYPE,
                    JiraIssueField.STATUS,
                    JiraIssueField.CREATED,
                }),
            ),
            self._jira.get_issues(
                resolved_jql, max_results=None,
                fields=frozenset({
                    JiraIssueField.SUMMARY,
                    JiraIssueField.ISSUE_TYPE,
                    JiraIssueField.STATUS,
                    JiraIssueField.RESOLVED,
                }),
            ),
        )
        def _to_created(issue: JiraIssue) -> CreatedResolvedIssueDetail:
            return CreatedResolvedIssueDetail(
                key=issue.key,
                summary=issue.summary[:60],
                type=issue.issue_type or "기타",
                status=issue.status or "기타",
                created=issue.created[:16].replace("T", " "),
            )

        def _to_resolved(issue: JiraIssue) -> ResolvedIssueDetail:
            return ResolvedIssueDetail(
                key=issue.key,
                summary=issue.summary[:60],
                type=issue.issue_type or "기타",
                status=issue.status or "기타",
                resolved=issue.resolved[:16].replace("T", " "),
            )

        created_details  = [_to_created(i)  for i in created_issues]
        resolved_details = [_to_resolved(i) for i in resolved_issues]
        logger.info(f"[w3-생성vs해결] 생성 {len(created_details)}건 / 해결 {len(resolved_details)}건")
        return WidgetResult(
            name="주간 생성 vs 해결",
            total=len(created_details),
            jql=created_jql,
            data=CreatedVsResolvedWidgetData(
                created=len(created_details),
                resolved=len(resolved_details),
                created_details=created_details,
                resolved_details=resolved_details,
            ),
        )
