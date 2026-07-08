# backend/src/application/widgets/sla_delay_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SlaDelayWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class SlaDelayCollector(AbstractWidgetCollector):
    """w10: SLA 지연 사유 (by_status 분류)."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries, sla_threshold_days: int):
        self._jira = jira
        self._q = q
        self._threshold = sla_threshold_days

    async def collect(self) -> WidgetResult[SlaDelayWidgetData]:
        jql = self._q.w10_sla_violated()
        issues = await self._jira.get_issues(
            jql, max_results=500, fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        by_status: dict[str, int] = {}
        for issue in issues:
            fields = issue.get("fields") or {}
            status = (fields.get("status") or {}).get("name", "알 수 없음")
            created = fields.get("created", "")
            if created:
                elapsed = (now_ts - datetime.fromisoformat(created[:19])).days
                if elapsed >= self._threshold:
                    by_status[status] = by_status.get(status, 0) + 1
        total = sum(by_status.values())
        logger.info(f"[w10-SLA지연사유] {total}건")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            data=SlaDelayWidgetData(by_status=by_status),
        )
