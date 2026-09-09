# backend/src/application/widgets/sla_delay_collector.py
import logging

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SlaDelayIssueDetail, SlaDelayWidgetData
from src.application.ports.jira_port import JiraPort
from src.domain.constants import SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)


class SlaDelayCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[SlaDelayWidgetData]:
        jql = self._q.w12_sla()
        issues = await self._jira.get_issues_with_sla(jql, max_results=None)

        by_status: dict[str, int] = {}
        by_status_details: dict[str, list[SlaDelayIssueDetail]] = {}

        for issue in issues:
            initial_breached = issue.initial_response_breached
            resolution_breached = issue.resolution_breached
            if not (initial_breached or resolution_breached):
                continue

            status = issue.status or "알 수 없음"
            by_status[status] = by_status.get(status, 0) + 1

            detail = SlaDelayIssueDetail(
                key=issue.key,
                summary=issue.summary[:SUMMARY_TRUNCATE_LEN],
                type=issue.issue_type or "기타",
                status=status,
                created=issue.created[:16].replace("T", " "),
            )
            by_status_details.setdefault(status, []).append(detail)

        total = sum(by_status.values())
        logger.info(f"[w13-SLA지연사유] {total}건")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            data=SlaDelayWidgetData(
                by_status=by_status,
                by_status_details=by_status_details,
            ),
        )
