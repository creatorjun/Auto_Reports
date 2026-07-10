# backend/src/application/services/report_assembler.py
import asyncio
import logging
from datetime import datetime
from typing import Callable

from src.application.services.query_builder import ResolvedQueries, WidgetQueryBuilder
from src.application.widgets.collector_factory import CollectorEntry
from src.domain.entities.report import NewReport
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.widget_id import WidgetId
from src.shared.constants import KST

logger = logging.getLogger(__name__)

BaseCollectorFactory = Callable[[ResolvedQueries, datetime], list[CollectorEntry]]
MonthlyCollectorFactory = Callable[[ResolvedQueries, datetime], list[tuple[WidgetId, object]]]


class ReportAssembler:
    def __init__(
        self,
        query_builder: WidgetQueryBuilder,
        base_collector_factory: BaseCollectorFactory,
        monthly_collector_factory: MonthlyCollectorFactory,
    ):
        self._qb = query_builder
        self._base_factory = base_collector_factory
        self._monthly_factory = monthly_collector_factory

    async def collect(
        self,
        now: datetime,
        week_start_override: datetime | None = None,
    ) -> NewReport:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        q = self._qb.build(now, week_start_override=week_start_override)
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        entries: list[CollectorEntry] = self._base_factory(q, now)
        monthly_pairs = self._monthly_factory(q, now)

        base_results = await asyncio.gather(*[e.collector.collect() for e in entries])
        monthly_results_nested = await asyncio.gather(*[collector.collect() for _, collector in monthly_pairs])

        widgets: dict[WidgetId, WidgetResult] = {
            e.widget_id: result for e, result in zip(entries, base_results)
        }
        for (widget_id, _), results in zip(monthly_pairs, monthly_results_nested):
            if isinstance(results, tuple):
                for wid, res in zip(
                    [WidgetId.SLA_INITIAL_RESPONSE, WidgetId.SLA_RESOLUTION_MONTHLY]
                    if widget_id == WidgetId.SLA_INITIAL_RESPONSE
                    else [WidgetId.MONTHLY_CREATED, WidgetId.MONTHLY_RESOLVED],
                    results,
                ):
                    widgets[wid] = res
            else:
                widgets[widget_id] = results

        logger.info("데이터 수집 완료 ✅")
        return NewReport(
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets,
        )
