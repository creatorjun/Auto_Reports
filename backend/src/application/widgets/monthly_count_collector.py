# backend/src/application/widgets/monthly_count_collector.py
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
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

        created_jqls = [self._q.w8_monthly_created(y, m) for y, m in months]
        resolved_jqls = [self._q.w9_monthly_resolved(y, m) for y, m in months]
        base_jqls = created_jqls + resolved_jqls
        query_groups = [
            [
                *self._q.by_issue_type(jql).values(),
                self._q.outside_issue_types(jql),
            ]
            for jql in base_jqls
        ]
        all_jqls = [jql for queries in query_groups for jql in queries]

        all_counts = await self._jira.get_issue_counts_batch(all_jqls)
        issue_types = list(self._q.issue_types)
        group_size = len(issue_types) + 1
        grouped_counts = [
            (
                dict(zip(issue_types, all_counts[index:index + group_size - 1])),
                all_counts[index + group_size - 1],
            )
            for index in range(0, len(all_counts), group_size)
        ]
        created_counts = grouped_counts[:len(months)]
        resolved_counts = grouped_counts[len(months):]

        w8_entries: list[MonthlyCountEntry] = []
        w9_entries: list[MonthlyCountEntry] = []
        for (y, m), created, resolved in zip(months, created_counts, resolved_counts):
            created_by_type, created_always_included = created
            resolved_by_type, resolved_always_included = resolved
            label = f"{m}월"
            w8_entries.append(MonthlyCountEntry(
                month=label,
                year=y,
                month_num=m,
                count=sum(created_by_type.values()) + created_always_included,
                by_type=created_by_type,
                always_included=created_always_included,
            ))
            w9_entries.append(MonthlyCountEntry(
                month=label,
                year=y,
                month_num=m,
                count=sum(resolved_by_type.values()) + resolved_always_included,
                by_type=resolved_by_type,
                always_included=resolved_always_included,
            ))

        logger.info(
            f"[w8/w9] 월별 등록/해결 {self._now.year}년 수집 완료 "
            f"(배치 {len(all_jqls)}건 JQL → 단일 gather)"
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
