# backend/src/application/widgets/recent_collector.py
import logging
from typing import Any

from src.application.services.query_builder import QueryBuilder
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId
from src.shared.constants import JIRA_RECENT_MAX_RESULTS
from src.shared.widget_result import WidgetResult

logger = logging.getLogger(__name__)


class RecentIssueWidgetData:
    def __init__(self, issue_details: list[dict[str, Any]]):
        self.issue_details = issue_details


class RecentCollector:
    def __init__(self, jira: JiraPort, q: QueryBuilder):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w12_recent()
        issues = await self._jira.get_issues_with_assignees(
            jql, max_results=JIRA_RECENT_MAX_RESULTS
        )
        return WidgetResult(
            widget_id=WidgetId.RECENT_ISSUES,
            data=RecentIssueWidgetData(issue_details=issues),
        )
