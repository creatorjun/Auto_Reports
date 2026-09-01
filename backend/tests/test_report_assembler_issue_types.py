# backend/tests/test_report_assembler_issue_types.py
import datetime
import unittest

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.widgets.collector_factory import CollectorEntry
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.widget_id import WidgetId


class StaticCollector:
    async def collect(self) -> WidgetResult:
        return WidgetResult(name="연간 생성", total=0)


class ReportAssemblerIssueTypesTest(unittest.IsolatedAsyncioTestCase):
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
            ["인시던트", "H/W 장애 요청", "승인된 서비스 요청"],
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

        self.assertEqual(["기본 유형"], captured_types)
