# backend/src/application/widgets/monthly_collector.py
import asyncio
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    MonthlyEntry,
    SlaMonthlyTypeStats,
    SlaMonthlyWidgetData,
)
from src.application.ports.jira_port import JiraPort
from src.domain.constants import JIRA_MAX_RESULT

logger = logging.getLogger(__name__)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"


class MonthlyCollector(AbstractWidgetCollector):
    MONTHS_BACK = 6

    def __init__(self, jira: JiraPort, q: ResolvedQueries, now: datetime):
        self._jira = jira
        self._q = q
        self._now = now

    async def collect(self) -> Tuple[WidgetResult, WidgetResult]:
        year, month = self._now.year, self._now.month
        months: list[tuple[int, int]] = []
        for _ in range(self.MONTHS_BACK):
            months.insert(0, (year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1

        async def _fetch_month(y: int, m: int) -> tuple[int, int, list]:
            jql = self._q.w10_w11_monthly_candidates(y, m)
            issues = await self._jira.get_issues_with_sla(
                jql, max_results=JIRA_MAX_RESULT, extra_fields="resolutiondate"
            )
            return y, m, issues

        month_results = await asyncio.gather(*[_fetch_month(y, m) for y, m in months])

        w10_entries: list[MonthlyEntry] = []
        w11_entries: list[MonthlyEntry] = []

        for y, m, issues in month_results:
            init_by_type = {
                issue_type: SlaMonthlyTypeStats(met=0, total=0)
                for issue_type in self._q.issue_types
            }
            res_by_type = {
                issue_type: SlaMonthlyTypeStats(met=0, total=0)
                for issue_type in self._q.issue_types
            }
            for issue in issues:
                fields = issue.get("fields") or {}
                issue_type = (fields.get("issuetype") or {}).get("name", "기타")
                if issue_type not in init_by_type:
                    continue
                init_stats = init_by_type[issue_type]
                res_stats = res_by_type[issue_type]
                init_stats.total += 1
                res_stats.total += 1
                if not self._breached(fields.get(_SLA_INITIAL_KEY)):
                    init_stats.met += 1
                if not self._breached(fields.get(_SLA_RESOLUTION_KEY)):
                    res_stats.met += 1

            total = sum(stats.total for stats in init_by_type.values())
            init_met = sum(stats.met for stats in init_by_type.values())
            res_met = sum(stats.met for stats in res_by_type.values())
            init_rate = round(init_met / total * 100, 1) if total > 0 else 0.0
            res_rate  = round(res_met  / total * 100, 1) if total > 0 else 0.0

            label = f"{y}-{m:02d}"
            w10_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=init_rate, met=init_met, total=total,
                by_type=init_by_type,
            ))
            w11_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=res_rate, met=res_met, total=total,
                by_type=res_by_type,
            ))

        logger.info(f"[w10/w11] 월별 SLA {self.MONTHS_BACK}개월 수집 완료")
        return (
            WidgetResult(name="최초응답 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w10_entries)),
            WidgetResult(name="해결시간 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w11_entries)),
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
