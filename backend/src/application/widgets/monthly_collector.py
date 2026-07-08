# backend/src/application/widgets/monthly_collector.py
import asyncio
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import MonthlyEntry, SlaMonthlyWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class MonthlyCollector:
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
        self._w15_fid = sla_initial_response_field_id
        self._w16_fid = sla_resolution_field_id

    async def collect(self) -> tuple[WidgetResult[SlaMonthlyWidgetData], WidgetResult[SlaMonthlyWidgetData]]:
        fields_str = f"summary,issuetype,created,resolutiondate,{self._w15_fid},{self._w16_fid}"
        months = self._last_six_months(self._now)

        async def _fetch_month(year: int, month: int):
            jql = self._q.w15_w16_monthly_candidates(year, month)
            issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)
            return year, month, issues

        month_data = await asyncio.gather(*[_fetch_month(y, m) for y, m in months])

        w15 = self._build_monthly_result(month_data, self._w15_fid, "최초 응답 SLA (최근 6개월)")
        w16 = self._build_monthly_result(month_data, self._w16_fid, "해결시간 SLA (최근 6개월)")
        return w15, w16

    def _build_monthly_result(
        self,
        month_data_list,
        field_id: str,
        widget_name: str,
    ) -> WidgetResult[SlaMonthlyWidgetData]:
        monthly: list[MonthlyEntry] = []
        total_met = 0
        total_all = 0
        for year, month, issues in month_data_list:
            counts = self._calc_monthly(issues, field_id)
            total = counts["met"] + counts["breached"]
            rate = round(counts["met"] / total * 100, 1) if total > 0 else 0.0
            monthly.append(
                MonthlyEntry(
                    month=f"{month}월",
                    year=year,
                    month_num=month,
                    rate=rate,
                    met=counts["met"],
                    total=total,
                )
            )
            total_met += counts["met"]
            total_all += total
        overall_rate = round(total_met / total_all * 100, 1) if total_all > 0 else 0.0
        logger.info(f"[{widget_name}] field={field_id} 6개월 종합 {overall_rate}% ({total_met}/{total_all})")
        return WidgetResult(
            name=widget_name,
            total=total_all,
            data=SlaMonthlyWidgetData(monthly=monthly),
        )

    @staticmethod
    def _calc_monthly(issues: list, field_id: str) -> dict[str, int]:
        met = breached = 0
        for issue in issues:
            sla_value = (issue.get("fields") or {}).get(field_id)
            if not sla_value:
                continue
            counts = MonthlyCollector._count_sla_cycles(sla_value)
            met += counts["met"]
            breached += counts["breached"]
        return {"met": met, "breached": breached}

    @staticmethod
    def _count_sla_cycles(sla_value: dict) -> dict[str, int]:
        met = breached = 0
        for cycle in sla_value.get("completedCycles") or []:
            if cycle.get("breached"):
                breached += 1
            else:
                met += 1
        ongoing = sla_value.get("ongoingCycle")
        if ongoing:
            if ongoing.get("breached"):
                breached += 1
            else:
                met += 1
        return {"met": met, "breached": breached}

    @staticmethod
    def _last_six_months(now: datetime) -> list[tuple[int, int]]:
        result = []
        year, month = now.year, now.month
        for _ in range(6):
            result.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return list(reversed(result))
