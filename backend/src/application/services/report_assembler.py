# backend/src/application/services/report_assembler.py
import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable

from src.application.services.query_builder import ResolvedQueries, WidgetQueryBuilder
from src.application.widgets.collector_factory import CollectorEntry
from src.domain.entities.report import NewReport
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.widget_id import WidgetId
from src.domain.constants import KST

logger = logging.getLogger(__name__)

BaseCollectorFactory = Callable[[ResolvedQueries, datetime], list[CollectorEntry]]
MonthlyCollectorFactory = Callable[[ResolvedQueries, datetime], list[tuple[list[WidgetId], object]]]
IssueTypeProvider = Callable[[], Awaitable[list[str]]]


class ReportAssembler:
    def __init__(
        self,
        query_builder: WidgetQueryBuilder,
        base_collector_factory: BaseCollectorFactory,
        monthly_collector_factory: MonthlyCollectorFactory,
        issue_type_provider: IssueTypeProvider | None = None,
    ):
        self._qb = query_builder
        self._base_factory = base_collector_factory
        self._monthly_factory = monthly_collector_factory
        self._issue_type_provider = issue_type_provider

    async def collect(
        self,
        now: datetime,
        week_start_override: datetime | None = None,
    ) -> NewReport:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        issue_types: list[str] | None = None
        if self._issue_type_provider is not None:
            try:
                discovered_types = await self._issue_type_provider()
                if discovered_types:
                    issue_types = discovered_types
                else:
                    logger.warning("Jira 요청 유형 목록이 비어 있어 ISSUE_TYPES 기본값을 사용합니다.")
            except Exception as exc:
                logger.warning(f"Jira 요청 유형 조회 실패로 ISSUE_TYPES 기본값을 사용합니다: {exc}")
        q = self._qb.build(
            now,
            week_start_override=week_start_override,
            issue_types_override=issue_types,
        )
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        entries: list[CollectorEntry] = self._base_factory(q, now)
        monthly_pairs = self._monthly_factory(q, now)

        base_coros = [e.collector.collect() for e in entries]
        monthly_coros = [collector.collect() for _, collector in monthly_pairs]
        all_results = await asyncio.gather(*base_coros, *monthly_coros)

        base_results = all_results[:len(entries)]
        monthly_results_nested = all_results[len(entries):]

        collected_widgets: dict[WidgetId, WidgetResult] = {
            e.widget_id: result for e, result in zip(entries, base_results)
        }

        for (widget_ids, _), results in zip(monthly_pairs, monthly_results_nested):
            ids = widget_ids if isinstance(widget_ids, list) else [widget_ids]
            if isinstance(results, tuple):
                for wid, res in zip(ids, results):
                    collected_widgets[wid] = res
            else:
                collected_widgets[ids[0]] = results

        widgets = {
            widget_id: collected_widgets[widget_id]
            for widget_id in WidgetId
            if widget_id in collected_widgets
        }

        logger.info("데이터 수집 완료 ✅")
        return NewReport(
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets,
        )
