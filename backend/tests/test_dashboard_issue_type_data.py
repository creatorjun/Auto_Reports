# backend/tests/test_dashboard_issue_type_data.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.count_collector import TypeCountCollector
from src.application.widgets.monthly_collector import MonthlyCollector
from src.application.widgets.monthly_count_collector import MonthlyCountCollector
from src.domain.entities.widget_data import TypeCountWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class BatchCountJira:
    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]:
        return [2 if 'issuetype = "라이선스"' in jql else 3 for jql in jqls]


class SlaJira:
    async def get_issues_with_sla(self, jql: str, max_results: int, extra_fields: str = "") -> list[dict]:
        return [
            {
                "fields": {
                    "issuetype": {"name": "인시던트"},
                    "_sla_initial": {"completedCycles": [{"breached": False}]},
                    "_sla_resolution": {"completedCycles": [{"breached": False}]},
                },
            },
            {
                "fields": {
                    "issuetype": {"name": "라이선스"},
                    "_sla_initial": {"completedCycles": [{"breached": True}]},
                    "_sla_resolution": {"completedCycles": [{"breached": False}]},
                },
            },
            {
                "fields": {
                    "issuetype": {"name": "토글 외 요청"},
                    "_sla_initial": {"completedCycles": [{"breached": False}]},
                    "_sla_resolution": {"completedCycles": [{"breached": True}]},
                },
            },
        ]


class DashboardIssueTypeDataTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = QueryConfig(
            project_key="TACEA",
            issue_types=["인시던트", "라이선스"],
            active_statuses=["처리 중"],
            closed_statuses=["Closed"],
            sla_threshold_days=30,
            year_start=2026,
        )
        self.now = datetime.datetime(2026, 8, 21)
        self.queries = WidgetQueryBuilder(config).build(self.now)

    async def test_yearly_counts_keep_every_issue_type(self) -> None:
        jql = self.queries.w1_yearly_created()
        collector = TypeCountCollector(
            BatchCountJira(),
            "연간 생성",
            jql,
            self.queries.by_issue_type(jql),
            self.queries.outside_issue_types(jql),
        )

        result = await collector.collect()

        self.assertEqual(8, result.total)
        self.assertIsInstance(result.data, TypeCountWidgetData)
        self.assertEqual(["인시던트", "라이선스"], result.data.issue_types)
        self.assertEqual({"인시던트": 3, "라이선스": 2}, result.data.by_type)
        self.assertEqual(3, result.data.always_included)

        restored = deserialize_widget(
            WidgetId.YEARLY_CREATED,
            serialize_widget(result),
        )
        self.assertEqual(3, restored.data.always_included)

    async def test_monthly_counts_keep_type_breakdowns(self) -> None:
        created, resolved = await MonthlyCountCollector(
            BatchCountJira(),
            self.queries,
            self.now,
        ).collect()

        first_created = created.data.monthly[0]
        first_resolved = resolved.data.monthly[0]
        self.assertEqual(12, len(created.data.monthly))
        self.assertEqual((2026, 1), (first_created.year, first_created.month_num))
        self.assertEqual((2026, 12), (
            created.data.monthly[-1].year,
            created.data.monthly[-1].month_num,
        ))
        self.assertEqual(8, first_created.count)
        self.assertEqual({"인시던트": 3, "라이선스": 2}, first_created.by_type)
        self.assertEqual(3, first_created.always_included)
        self.assertEqual(8, first_resolved.count)
        self.assertEqual({"인시던트": 3, "라이선스": 2}, first_resolved.by_type)
        self.assertEqual(3, first_resolved.always_included)

        restored = deserialize_widget(
            WidgetId.MONTHLY_CREATED,
            serialize_widget(created),
        )
        self.assertEqual(3, restored.data.monthly[0].always_included)

    async def test_monthly_sla_keeps_met_and_total_by_type(self) -> None:
        initial, resolution = await MonthlyCollector(
            SlaJira(),
            self.queries,
            self.now,
        ).collect()

        initial_entry = initial.data.monthly[0]
        resolution_entry = resolution.data.monthly[0]
        self.assertEqual(12, len(initial.data.monthly))
        self.assertEqual((2026, 1), (initial_entry.year, initial_entry.month_num))
        self.assertEqual((2026, 12), (
            initial.data.monthly[-1].year,
            initial.data.monthly[-1].month_num,
        ))
        self.assertEqual((1, 1), (
            initial_entry.by_type["인시던트"].met,
            initial_entry.by_type["인시던트"].total,
        ))
        self.assertEqual((0, 1), (
            initial_entry.by_type["라이선스"].met,
            initial_entry.by_type["라이선스"].total,
        ))
        self.assertEqual((1, 1), (
            resolution_entry.by_type["라이선스"].met,
            resolution_entry.by_type["라이선스"].total,
        ))
        self.assertEqual((1, 1), (
            initial_entry.always_included.met,
            initial_entry.always_included.total,
        ))
        self.assertEqual((0, 1), (
            resolution_entry.always_included.met,
            resolution_entry.always_included.total,
        ))

        restored = deserialize_widget(
            WidgetId.SLA_INITIAL_RESPONSE,
            serialize_widget(initial),
        )
        restored_stats = restored.data.monthly[0].by_type["라이선스"]
        self.assertEqual((0, 1), (restored_stats.met, restored_stats.total))
        restored_always = restored.data.monthly[0].always_included
        self.assertEqual((1, 1), (restored_always.met, restored_always.total))
