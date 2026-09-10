# backend/tests/test_report_assembler_issue_types.py
import datetime
import unittest

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.widgets.collector_factory import CollectorEntry
from src.domain.constants import KST
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.config.settings import Settings


class StaticCollector:
    async def collect(self) -> WidgetResult:
        return WidgetResult(name="연간 생성", total=0)


class ReportAssemblerIssueTypesTest(unittest.IsolatedAsyncioTestCase):
    def test_default_issue_types_include_the_canonical_jira_license_name(self) -> None:
        self.assertIn("라이선스", Settings.model_fields["issue_types"].default)

    def setUp(self) -> None:
        self.query_builder = WidgetQueryBuilder(QueryConfig(
            project_key="TACEA",
            issue_types=["기본 유형", "라이선스"],
            active_statuses=[],
            closed_statuses=["Closed"],
            sla_threshold_days=30,
            year_start=2026,
        ))

    async def test_uses_all_issue_types_discovered_from_jira(self) -> None:
        captured_types: list[str] = []

        async def issue_type_provider() -> list[str]:
            return ["인시던트", "라이선스", "H/W 장애 요청", "승인된 서비스 요청"]

        def base_factory(queries, now):
            captured_types.extend(queries.issue_types)
            return [CollectorEntry(WidgetId.YEARLY_CREATED, StaticCollector())]

        assembler = ReportAssembler(
            query_builder=self.query_builder,
            base_collector_factory=base_factory,
            monthly_collector_factory=lambda queries, now: [],
            issue_type_provider=issue_type_provider,
        )

        await assembler.collect(datetime.datetime(2026, 8, 24))

        self.assertEqual(
            ["인시던트", "라이선스", "H/W 장애 요청", "승인된 서비스 요청"],
            captured_types,
        )

    async def test_uses_configured_types_when_jira_lookup_fails(self) -> None:
        captured_types: list[str] = []

        async def issue_type_provider() -> list[str]:
            raise RuntimeError("metadata unavailable")

        def base_factory(queries, now):
            captured_types.extend(queries.issue_types)
            return [CollectorEntry(WidgetId.YEARLY_CREATED, StaticCollector())]

        assembler = ReportAssembler(
            query_builder=self.query_builder,
            base_collector_factory=base_factory,
            monthly_collector_factory=lambda queries, now: [],
            issue_type_provider=issue_type_provider,
        )

        await assembler.collect(datetime.datetime(2026, 8, 24))

        self.assertEqual(["기본 유형", "라이선스"], captured_types)

    async def test_current_collection_time_is_separate_from_historical_period(self) -> None:
        period_end = datetime.datetime(2025, 12, 31, 23, 59, tzinfo=KST)
        period_start = datetime.datetime(2025, 1, 1, tzinfo=KST)
        collected_at = datetime.datetime(2026, 9, 10, 0, 5, tzinfo=KST)
        captured = {}

        def base_factory(queries, now):
            captured["base"] = (queries.week_start, queries.week_end, now)
            return [CollectorEntry(WidgetId.YEARLY_CREATED, StaticCollector())]

        def monthly_factory(queries, now):
            captured["monthly"] = now
            return []

        def annual_factory(queries, now):
            captured["annual"] = now
            return []

        assembler = ReportAssembler(
            query_builder=self.query_builder,
            base_collector_factory=base_factory,
            monthly_collector_factory=monthly_factory,
            annual_collector_factory=annual_factory,
        )

        report = await assembler.collect(
            period_end,
            week_start_override=period_start,
            annual_report_year=2025,
            collected_at=collected_at,
        )

        self.assertEqual((period_start, period_end, collected_at), captured["base"])
        self.assertEqual(period_end, captured["monthly"])
        self.assertEqual(period_end, captured["annual"])
        self.assertEqual(period_start.date(), report.week_start)
        self.assertEqual(period_end.date(), report.week_end)
