# backend/src/application/widgets/monthly_collector.py
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.application.widgets.issue_breakdown import issue_status_name, issue_type_name
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    MonthlyEntry,
    SlaMonthlyTypeStats,
    SlaMonthlyWidgetData,
)
from src.application.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"


class MonthlyCollector(AbstractWidgetCollector):
    MONTHS_PER_YEAR = 12

    def __init__(self, jira: JiraPort, q: ResolvedQueries, now: datetime):
        self._jira = jira
        self._q = q
        self._now = now

    async def collect(self) -> Tuple[WidgetResult, WidgetResult]:
        months = [
            (self._now.year, month)
            for month in range(1, self.MONTHS_PER_YEAR + 1)
        ]

        issues = await self._jira.get_issues_with_sla(
            self._q.w1_yearly_created(),
            max_results=None,
            extra_fields="resolutiondate",
        )
        issues_by_month = self._bucket_by_created_month(issues, months)

        w10_entries: list[MonthlyEntry] = []
        w11_entries: list[MonthlyEntry] = []

        for y, m in months:
            month_issues = issues_by_month[(y, m)]
            init_by_type = {
                issue_type: SlaMonthlyTypeStats(met=0, total=0)
                for issue_type in self._q.issue_types
            }
            res_by_type = {
                issue_type: SlaMonthlyTypeStats(met=0, total=0)
                for issue_type in self._q.issue_types
            }
            init_always_included = SlaMonthlyTypeStats(met=0, total=0)
            res_always_included = SlaMonthlyTypeStats(met=0, total=0)
            init_by_status_type: dict[str, dict[str, SlaMonthlyTypeStats]] = {}
            res_by_status_type: dict[str, dict[str, SlaMonthlyTypeStats]] = {}
            for issue in month_issues:
                fields = issue.get("fields") or {}
                issue_type = issue_type_name(issue)
                status = issue_status_name(issue)
                init_stats = init_by_type.get(issue_type, init_always_included)
                res_stats = res_by_type.get(issue_type, res_always_included)
                init_status_stats = init_by_status_type.setdefault(status, {}).setdefault(
                    issue_type,
                    SlaMonthlyTypeStats(),
                )
                res_status_stats = res_by_status_type.setdefault(status, {}).setdefault(
                    issue_type,
                    SlaMonthlyTypeStats(),
                )
                init_stats.total += 1
                res_stats.total += 1
                init_status_stats.total += 1
                res_status_stats.total += 1
                if not self._breached(fields.get(_SLA_INITIAL_KEY)):
                    init_stats.met += 1
                    init_status_stats.met += 1
                if not self._breached(fields.get(_SLA_RESOLUTION_KEY)):
                    res_stats.met += 1
                    res_status_stats.met += 1

            total = sum(stats.total for stats in init_by_type.values()) + init_always_included.total
            init_met = sum(stats.met for stats in init_by_type.values()) + init_always_included.met
            res_met = sum(stats.met for stats in res_by_type.values()) + res_always_included.met
            init_rate = round(init_met / total * 100, 1) if total > 0 else 0.0
            res_rate  = round(res_met  / total * 100, 1) if total > 0 else 0.0

            label = f"{y}-{m:02d}"
            w10_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=init_rate, met=init_met, total=total,
                by_type=init_by_type,
                always_included=init_always_included,
                by_status_type=init_by_status_type,
            ))
            w11_entries.append(MonthlyEntry(
                month=label, year=y, month_num=m,
                rate=res_rate, met=res_met, total=total,
                by_type=res_by_type,
                always_included=res_always_included,
                by_status_type=res_by_status_type,
            ))

        logger.info(f"[w10/w11] 월별 SLA {self._now.year}년 수집 완료")
        return (
            WidgetResult(name="최초응답 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w10_entries)),
            WidgetResult(name="해결시간 SLA 월별", total=0, data=SlaMonthlyWidgetData(monthly=w11_entries)),
        )

    @staticmethod
    def _bucket_by_created_month(
        issues: list[dict],
        months: list[tuple[int, int]],
    ) -> dict[tuple[int, int], list[dict]]:
        buckets = {month: [] for month in months}
        for issue in issues:
            created = str((issue.get("fields") or {}).get("created") or "")
            try:
                key = (int(created[:4]), int(created[5:7]))
            except ValueError:
                continue
            if key in buckets:
                buckets[key].append(issue)
        return buckets

    @staticmethod
    def _breached(sla_val: dict | None) -> bool:
        if not sla_val:
            return False
        for cycle in sla_val.get("completedCycles") or []:
            if cycle.get("breached"):
                return True
        ongoing = sla_val.get("ongoingCycle")
        return bool(ongoing and ongoing.get("breached"))
