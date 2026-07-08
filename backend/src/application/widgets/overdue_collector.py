# backend/src/application/widgets/overdue_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import IssueDetail, OverdueWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class OverdueCollector(AbstractWidgetCollector):
    """w12: SLA 초과 지연 이슈 상세."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries, sla_threshold_days: int):
        self._jira = jira
        self._q = q
        self._threshold = sla_threshold_days

    async def collect(self) -> WidgetResult[OverdueWidgetData]:
        jql = self._q.w12_overdue()
        by_type_status = self._q.w12_by_type_status()
        issues = await self._jira.get_issues(
            jql, max_results=200, fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        details: list[IssueDetail] = []
        for issue in issues:
            fields = issue.get("fields") or {}
            created = fields.get("created", "")
            elapsed_days = 0
            if created:
                elapsed_days = (now_ts - datetime.fromisoformat(created[:19])).days
            details.append(
                IssueDetail(
                    key=issue.get("key", ""),
                    summary=(fields.get("summary") or "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=(fields.get("status") or {}).get("name", "기타"),
                    created=created[:16].replace("T", " "),
                    elapsed_days=elapsed_days,
                )
            )
        details.sort(key=lambda x: x.elapsed_days, reverse=True)
        total = len(details)
        logger.info(f"[w12-SLA초과] {total}건")
        return WidgetResult(
            name="SLA 초과 지연 이슈",
            total=total,
            jql=jql,
            data=OverdueWidgetData(issue_details=details),
        )
