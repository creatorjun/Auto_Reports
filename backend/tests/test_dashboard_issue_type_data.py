# backend/tests/test_dashboard_issue_type_data.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.ports.jira_port import JiraIssue, JiraIssueField
from src.application.widgets.count_collector import TypeCountCollector
from src.application.widgets.monthly_collector import MonthlyCollector
from src.application.widgets.monthly_count_collector import MonthlyCountCollector
from src.domain.entities.widget_data import TypeCountWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class BatchCountJira:
    async def get_issues(self, jql: str, max_results: int | None, fields: frozenset[JiraIssueField]) -> list[JiraIssue]:
        if 'issuetype != "라이선스"' not in jql:
            raise AssertionError("라이선스 제외 조건이 필요합니다")
        if max_results is not None:
            raise AssertionError("상태별 집계는 전체 이슈를 수집해야 합니다")
        if fields != frozenset({
            JiraIssueField.ISSUE_TYPE,
            JiraIssueField.STATUS,
            JiraIssueField.CREATED,
            JiraIssueField.RESOLVED,
        }):
            raise AssertionError("상태, 요청 유형, 월 분류 필드가 필요합니다")
        return [
            JiraIssue(issue_type="인시던트", status="할 일", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
            JiraIssue(issue_type="인시던트", status="Closed", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
            JiraIssue(issue_type="인시던트", status="Closed", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
            JiraIssue(issue_type="토글 외 요청", status="할 일", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
            JiraIssue(issue_type="토글 외 요청", status="할 일", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
            JiraIssue(issue_type="토글 외 요청", status="Closed", created="2026-01-10T09:00:00.000+0900", resolved="2026-01-12T09:00:00.000+0900"),
        ]


class SlaJira:
    async def get_issues_with_sla(self, jql: str, max_results: int) -> list[JiraIssue]:
        if 'issuetype != "라이선스"' not in jql:
            raise AssertionError("라이선스 제외 조건이 필요합니다")
        return [
            JiraIssue(
                issue_type="인시던트",
                status="할 일",
                created="2026-01-10T09:00:00.000+0900",
            ),
            JiraIssue(
                issue_type="토글 외 요청",
                status="Closed",
                created="2026-01-11T09:00:00.000+0900",
                resolution_breached=True,
            ),
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

    async def test_yearly_counts_exclude_license_requests(self) -> None:
        jql = self.queries.w1_yearly_created()
        collector = TypeCountCollector(
            BatchCountJira(),
            "연간 생성",
            jql,
            list(self.queries.issue_types),
        )

        result = await collector.collect()

        self.assertEqual(6, result.total)
        self.assertIsInstance(result.data, TypeCountWidgetData)
        self.assertEqual(["인시던트"], result.data.issue_types)
        self.assertEqual({"인시던트": 3}, result.data.by_type)
        self.assertEqual(3, result.data.always_included)
        self.assertEqual({"인시던트": 1, "토글 외 요청": 2}, result.data.by_status_type["할 일"])
        self.assertEqual({"인시던트": 2, "토글 외 요청": 1}, result.data.by_status_type["Closed"])
        self.assertTrue(result.data.status_breakdown_available)

        restored = deserialize_widget(
            WidgetId.YEARLY_CREATED,
            serialize_widget(result),
        )
        self.assertEqual(3, restored.data.always_included)
        self.assertEqual(2, restored.data.by_status_type["Closed"]["인시던트"])
        self.assertTrue(restored.data.status_breakdown_available)

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
        self.assertEqual(6, first_created.count)
        self.assertEqual({"인시던트": 3}, first_created.by_type)
        self.assertEqual(3, first_created.always_included)
        self.assertEqual(1, first_created.by_status_type["할 일"]["인시던트"])
        self.assertEqual(6, first_resolved.count)
        self.assertEqual({"인시던트": 3}, first_resolved.by_type)
        self.assertEqual(3, first_resolved.always_included)
        self.assertEqual(1, first_resolved.by_status_type["Closed"]["토글 외 요청"])

        restored = deserialize_widget(
            WidgetId.MONTHLY_CREATED,
            serialize_widget(created),
        )
        self.assertEqual(3, restored.data.monthly[0].always_included)
        self.assertEqual(2, restored.data.monthly[0].by_status_type["할 일"]["토글 외 요청"])

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
        self.assertNotIn("라이선스", initial_entry.by_type)
        self.assertNotIn("라이선스", resolution_entry.by_type)
        self.assertEqual((1, 1), (
            initial_entry.always_included.met,
            initial_entry.always_included.total,
        ))
        self.assertEqual((0, 1), (
            resolution_entry.always_included.met,
            resolution_entry.always_included.total,
        ))
        self.assertEqual((1, 1), (
            initial_entry.by_status_type["할 일"]["인시던트"].met,
            initial_entry.by_status_type["할 일"]["인시던트"].total,
        ))
        self.assertEqual((0, 1), (
            resolution_entry.by_status_type["Closed"]["토글 외 요청"].met,
            resolution_entry.by_status_type["Closed"]["토글 외 요청"].total,
        ))

        restored = deserialize_widget(
            WidgetId.SLA_INITIAL_RESPONSE,
            serialize_widget(initial),
        )
        self.assertNotIn("라이선스", restored.data.monthly[0].by_type)
        restored_always = restored.data.monthly[0].always_included
        self.assertEqual((1, 1), (restored_always.met, restored_always.total))
        restored_status = restored.data.monthly[0].by_status_type["Closed"]["토글 외 요청"]
        self.assertEqual((1, 1), (restored_status.met, restored_status.total))

    async def test_legacy_widgets_keep_new_status_defaults_when_fields_are_missing(self) -> None:
        restored_count = deserialize_widget(
            WidgetId.YEARLY_CREATED,
            {
                "name": "기존 연간 생성",
                "total": 3,
                "data": {
                    "issue_types": ["인시던트"],
                    "by_type": {"인시던트": 3},
                    "always_included": 0,
                },
            },
        )
        restored_period = deserialize_widget(
            WidgetId.CREATED_VS_RESOLVED,
            {
                "name": "기존 기간 집계",
                "total": 1,
                "data": {
                    "created": 0,
                    "resolved": 1,
                    "created_details": [],
                    "resolved_details": [{
                        "key": "TACEA-1",
                        "summary": "기존 완료 이슈",
                        "type": "인시던트",
                        "resolved": "2026-01-10 09:00",
                    }],
                },
            },
        )

        self.assertFalse(restored_count.data.status_breakdown_available)
        self.assertEqual({}, restored_count.data.by_status_type)
        self.assertEqual("기타", restored_period.data.resolved_details[0].status)
