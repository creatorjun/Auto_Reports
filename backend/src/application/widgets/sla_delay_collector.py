# backend/src/application/widgets/sla_delay_collector.py
import logging

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SlaDelayIssueDetail, SlaDelayWidgetData
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULTS_LARGE, SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"


class SlaDelayCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[SlaDelayWidgetData]:
        jql = self._q.w9_sla()
        issues = await self._jira.get_issues_with_sla(jql, max_results=JIRA_MAX_RESULTS_LARGE)

        by_status: dict[str, int] = {}
        by_status_details: dict[str, list[SlaDelayIssueDetail]] = {}

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_breached    = self._is_sla_breached(fields.get(_SLA_INITIAL_KEY))
            resolution_breached = self._is_sla_breached(fields.get(_SLA_RESOLUTION_KEY))
            if not (initial_breached or resolution_breached):
                continue

            status = (fields.get("status") or {}).get("name", "알 수 없음")
            by_status[status] = by_status.get(status, 0) + 1

            created_raw = fields.get("created") or ""
            detail = SlaDelayIssueDetail(
                key=issue.get("key", ""),
                summary=(fields.get("summary") or "")[:SUMMARY_TRUNCATE_LEN],
                type=(fields.get("issuetype") or {}).get("name", "기타"),
                status=status,
                created=created_raw[:16].replace("T", " "),
            )
            by_status_details.setdefault(status, []).append(detail)

        total = sum(by_status.values())
        logger.info(f"[w10-SLA지연사유] {total}건")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            data=SlaDelayWidgetData(
                by_status=by_status,
                by_status_details=by_status_details,
            ),
        )

    @staticmethod
    def _is_sla_breached(sla_val: dict | None) -> bool:
        if not sla_val:
            return False
        for cycle in (sla_val.get("completedCycles") or []):
            if cycle.get("breached"):
                return True
        ongoing = sla_val.get("ongoingCycle")
        if ongoing and ongoing.get("breached"):
            return True
        return False
