# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueWidgetData, RecentIssueEntry
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class RecentCollector(AbstractWidgetCollector):
    """w12: 최근 활성 이슈 목록."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w12_recent()
        issues = await self._jira.get_issues(
            jql, max_results=50, fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        issue_details = []
        for idx, issue in enumerate(issues):
            fields = issue.get("fields") or {}
            created = fields.get("created", "")
            elapsed_days = (
                (now_ts - datetime.fromisoformat(created[:19])).days if created else 0
            )
            issue_details.append(
                RecentIssueEntry(
                    key=issue.get("key", ""),
                    summary=(fields.get("summary") or "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=(fields.get("status") or {}).get("name", "기타"),
                    stage_index=idx,
                    created=created[:16].replace("T", " "),
                    elapsed_days=elapsed_days,
                )
            )
        total = len(issue_details)
        logger.info(f"[w12-최근이슈] {total}건")
        return WidgetResult(
            name="최근 활성 이슈",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=issue_details),
        )
