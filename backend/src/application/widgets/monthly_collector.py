# backend/src/application/widgets/monthly_collector.py
import asyncio
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import MonthlyEntry, SlaMonthlyWidgetData
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULTS_LARGE

logger = logging.getLogger(__name__)


class MonthlyCollector(AbstractWidgetCollector):
    """w7(최초응답 SLA) 및 w8(해결시간 SLA) 월별 데이터 수집."""

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

        fields_str = f"summary,created,resolutiondate,{self._initial_fid},{self._resolution_fid}"

        async def _fetch_month(y: int, m: int) -> tuple[int, int, list]:
            jql = self._q.w7_w8_monthly_candidates(y, m)
            issues = await self._jira.get_issues(jql, max_results=JIRA_MAX_RESULTS_LARGE, fields=fields_str)
            return y, m, issues

        month_results = await asyncio.gather(*[_fetch_month(y, m) for y, m in months])

        w7_entries: list[MonthlyEntry] = []
        w8_entries: list[MonthlyEntry] = []

        for y, m, issues in month_results:
            total = len(issues)
            init_viol = sum(
                1 for i in issues
                if self._breached((i.get("fields") or {}).get(self._initial_fid))
            )
            res_viol = sum(
                1 for i in issues
                if self._breached((i.get("fields") or {}).get(self._resolution_fid))
            )
            init_met  = total - init_viol
            res_met   = total - res_viol
            init_rate = round(init_met / total * 100, 1) if total > 0 else 0.0
            res_rate  = round(res_met  / total * 100, 1) if total > 0 else 0.0

            label = f"{y}-{m:02d}"
            w7_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=init_rate, met=init_met, total=total,
            ))
            w8_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=res_rate, met=res_met, total=total,
            ))

        logger.info(f"[w7/w8] 월별 SLA {self.MONTHS_BACK}개월 수집 완료")
        return (
            WidgetResult(name="최초응답 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w7_entries)),
            WidgetResult(name="해결시간 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w8_entries)),
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
