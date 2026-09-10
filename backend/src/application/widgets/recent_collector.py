# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.issue_age import issue_created_display, issue_elapsed_days
from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueWidgetData, RecentIssueDetail
from src.application.ports.jira_port import JiraPort
from src.domain.constants import (
    STAGE_MAP,
    SUMMARY_TRUNCATE_LEN,
)

logger = logging.getLogger(__name__)

class RecentCollector(AbstractWidgetCollector):

    def __init__(self, jira: JiraPort, q: ResolvedQueries, now: datetime):
        self._jira = jira
        self._q = q
        self._now = now

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w7_recent()
        issues = await self._jira.get_issues_with_assignees(
            jql,
            max_results=None,
        )
        issue_details = []
        for issue in issues:
            created = issue.created
            status_name = issue.status or "기타"
            elapsed_days = issue_elapsed_days(created, self._now)
            reporter = issue.reporter or "미지정"
            tac_team = (
                issue.tac_assignee
                or issue.qa_assignee
                or issue.assignee
                or "미지정"
            )
            issue_details.append(
                RecentIssueDetail(
                    key=issue.key,
                    summary=issue.summary[:SUMMARY_TRUNCATE_LEN],
                    type=issue.issue_type or "기타",
                    status=status_name,
                    stage_index=STAGE_MAP.get(status_name, 0),
                    created=issue_created_display(created),
                    elapsed_days=elapsed_days,
                    reporter=reporter,
                    tac_team=tac_team,
                    tac_assignee=issue.recent_tac_assignee or "미지정",
                )
            )
        total = len(issue_details)
        logger.info(f"[w7-최근이슈] {total}건")
        return WidgetResult(
            name="최근 활성 이슈",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=issue_details),
        )
