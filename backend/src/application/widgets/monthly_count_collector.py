# backend/src/application/widgets/monthly_count_collector.py
import asyncio
import logging
from datetime import datetime
from typing import Tuple

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import MonthlyCountEntry, MonthlyCountWidgetData
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULTS_LARGE

logger = logging.getLogger(__name__)


class MonthlyCountCollector(AbstractWidgetCollector):
    MONTHS_BACK = 6

    def __init__(self, jira: JiraPort, q: ResolvedQueries, now: datetime):
        self._jira = jira
        self._q = q
        self._now = now

    async def collect(self) -> Tuple[WidgetResult, WidgetResult]:  # type: ignore[override]
        year, month = self._now.year, self._now.month
        months: list[tuple[int, int]] = []
        for _ in range(self.MONTHS_BACK):
            months.insert(0, (year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1

        async def _fetch(y: int, m: int) -> tuple[int, int, int, int]:
            created_jql  = self._q.w13_monthly_created(y, m)
            resolved_jql = self._q.w14_monthly_resolved(y, m)
            created_count, resolved_count = await asyncio.gather(
                self._jira.get_issue_count(created_jql),
                self._jira.get_issue_count(resolved_jql),
            )
            return y, m, created_count, resolved_count

        results = await asyncio.gather(*[_fetch(y, m) for y, m in months])

        w13_entries: list[MonthlyCountEntry] = []
        w14_entries: list[MonthlyCountEntry] = []
        for y, m, created, resolved in results:
            label = f"{m}월"
            w13_entries.append(MonthlyCountEntry(month=label, year=y, month_num=m, count=created))
            w14_entries.append(MonthlyCountEntry(month=label, year=y, month_num=m, count=resolved))

        logger.info(f"[w13/w14] 월별 등록/해결 {self.MONTHS_BACK}개월 수집 완료")
        return (
            WidgetResult(name="월별 등록 건수", total=sum(e.count for e in w13_entries), data=MonthlyCountWidgetData(monthly=w13_entries)),
            WidgetResult(name="월별 해결 건수", total=sum(e.count for e in w14_entries), data=MonthlyCountWidgetData(monthly=w14_entries)),
        )
