# backend/src/application/widgets/monthly_count_collector.py
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.application.widgets.issue_breakdown import count_issue_type_statuses
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import MonthlyCountEntry, MonthlyCountWidgetData
from src.application.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class MonthlyCountCollector(AbstractWidgetCollector):
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

        fields = "issuetype,status,created,resolutiondate"
        created_issues = await self._jira.get_issues(
            self._q.w1_yearly_created(),
            max_results=None,
            fields=fields,
        )
        resolved_issues = await self._jira.get_issues(
            self._q.w2_yearly_resolved(),
            max_results=None,
            fields=fields,
        )
        created_results = self._bucket_by_month(created_issues, "created", months)
        resolved_results = self._bucket_by_month(resolved_issues, "resolutiondate", months)

        w8_entries: list[MonthlyCountEntry] = []
        w9_entries: list[MonthlyCountEntry] = []
        for y, m in months:
            created_month_issues = created_results[(y, m)]
            resolved_month_issues = resolved_results[(y, m)]
            created_by_type, created_always_included, created_by_status_type = count_issue_type_statuses(
                created_month_issues,
                self._q.issue_types,
            )
            resolved_by_type, resolved_always_included, resolved_by_status_type = count_issue_type_statuses(
                resolved_month_issues,
                self._q.issue_types,
            )
            label = f"{m}월"
            w8_entries.append(MonthlyCountEntry(
                month=label,
                year=y,
                month_num=m,
                count=sum(created_by_type.values()) + created_always_included,
                by_type=created_by_type,
                always_included=created_always_included,
                by_status_type=created_by_status_type,
            ))
            w9_entries.append(MonthlyCountEntry(
                month=label,
                year=y,
                month_num=m,
                count=sum(resolved_by_type.values()) + resolved_always_included,
                by_type=resolved_by_type,
                always_included=resolved_always_included,
                by_status_type=resolved_by_status_type,
            ))

        logger.info(
            f"[w8/w9] 월별 등록/해결 {self._now.year}년 수집 완료 "
            "(연간 2건 JQL을 월별 상태·유형으로 분류)"
        )
        return (
            WidgetResult(
                name="월별 등록 건수",
                total=sum(e.count for e in w8_entries),
                data=MonthlyCountWidgetData(monthly=w8_entries),
            ),
            WidgetResult(
                name="월별 해결 건수",
                total=sum(e.count for e in w9_entries),
                data=MonthlyCountWidgetData(monthly=w9_entries),
            ),
        )

    @staticmethod
    def _bucket_by_month(
        issues: list[dict],
        field_name: str,
        months: list[tuple[int, int]],
    ) -> dict[tuple[int, int], list[dict]]:
        buckets = {month: [] for month in months}
        for issue in issues:
            raw_value = str((issue.get("fields") or {}).get(field_name) or "")
            try:
                key = (int(raw_value[:4]), int(raw_value[5:7]))
            except ValueError:
                continue
            if key in buckets:
                buckets[key].append(issue)
        return buckets
