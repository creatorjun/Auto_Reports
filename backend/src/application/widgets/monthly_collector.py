# backend/src/application/widgets/monthly_collector.py
import logging
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SlaMetVsViolatedEntry, SlaMonthlyWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


class MonthlyCollector(AbstractWidgetCollector):
    """w12(최초응답 SLA) 및 w13(해결시간 SLA) 월별 데이터 수집."""

    MONTHS_BACK = 6

    def __init__(
        self,
        jira: JiraPort,
        q: ResolvedQueries,
        now: datetime,
        sla_initial_response_field_id: str,
        sla_resolution_field_id: str,
    ):
        self._jira = jira
        self._q = q
        self._now = now
        self._initial_fid = sla_initial_response_field_id
        self._resolution_fid = sla_resolution_field_id

    async def collect(self) -> Tuple[WidgetResult, WidgetResult]:  # type: ignore[override]
        year, month = self._now.year, self._now.month
        months: list[tuple[int, int]] = []
        for _ in range(self.MONTHS_BACK):
            months.insert(0, (year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1

        w12_monthly: list[SlaMonthlyWidgetData] = []
        w13_monthly: list[SlaMonthlyWidgetData] = []

        for y, m in months:
            jql = self._q.w12_w13_monthly_candidates(y, m)
            fields_str = f"summary,created,resolutiondate,{self._initial_fid},{self._resolution_fid}"
            issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)

            total = len(issues)
            init_viol = sum(
                1 for i in issues
                if self._breached((i.get("fields") or {}).get(self._initial_fid))
            )
            res_viol = sum(
                1 for i in issues
                if self._breached((i.get("fields") or {}).get(self._resolution_fid))
            )
            label = f"{y}-{m:02d}"
            w12_monthly.append(SlaMonthlyWidgetData(month=label, total=total, violations=init_viol))
            w13_monthly.append(SlaMonthlyWidgetData(month=label, total=total, violations=res_viol))

        logger.info(f"[w12/w13] 월별 SLA {self.MONTHS_BACK}개월 수집 완료")
        return (
            WidgetResult(name="최초응답 SLA 월별", total=0, data=w12_monthly),
            WidgetResult(name="해결시간 SLA 월별", total=0, data=w13_monthly),
        )

    @staticmethod
    def _breached(sla_val: dict | None) -> bool:
        if not sla_val:
            return False
        for cycle in sla_val.get("completedCycles") or []:
            if cycle.get("breached"):
                return True
        ongoing = sla_val.get("ongoingCycle")
        return bool(ongoing and ongoing.get("breached"))
