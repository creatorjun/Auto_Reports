# backend/src/application/widgets/sla_delay_collector.py
import logging

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SlaDelayIssueDetail, SlaDelayWidgetData
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULTS_LARGE, SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)


class SlaDelayCollector(AbstractWidgetCollector):
    def __init__(
        self,
        jira: JiraPort,
        q: ResolvedQueries,
        sla_initial_response_field_id: str,
        sla_resolution_field_id: str,
    ):
        self._jira = jira
        self._q = q
        self._initial_fid = sla_initial_response_field_id
        self._resolution_fid = sla_resolution_field_id

    async def collect(self) -> WidgetResult[SlaDelayWidgetData]:
        fields_str = (
            f"summary,issuetype,status,created,"
            f"{self._initial_fid},{self._resolution_fid}"
        )
        jql = self._q.w9_sla()
        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULTS_LARGE, fields=fields_str
        )

        by_status: dict[str, int] = {}
        by_status_details: dict[str, list[SlaDelayIssueDetail]] = {}

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_breached = self._is_sla_breached(fields.get(self._initial_fid))
            resolution_breached = self._is_sla_breached(fields.get(self._resolution_fid))
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
