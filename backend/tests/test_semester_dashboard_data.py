# backend/tests/test_semester_dashboard_data.py
import datetime
import unittest

from src.application.ports.jira_port import JiraIssue, JiraIssueField
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.count_collector import SimpleWithDetailsCollector
from src.application.widgets.resolution_collector import ResolutionCollector
from src.domain.entities.widget_data import ResolutionTypeEntry
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class ResolutionJira:
    async def get_issues(self, jql: str, max_results: int, fields: frozenset[JiraIssueField]) -> list[JiraIssue]:
        return [
            JiraIssue(
                issue_type="인시던트",
                status="할 일",
                created="2026-01-10T00:00:00.000+0900",
                resolved="2026-03-10T00:00:00.000+0900",
            ),
            JiraIssue(
                issue_type="인시던트",
                status="Closed",
                created="2026-07-10T00:00:00.000+0900",
                resolved="2026-08-10T00:00:00.000+0900",
            ),
        ]


class CreatedResolvedJira:
    async def get_issues(self, jql: str, max_results: int | None, fields: frozenset[JiraIssueField]) -> list[JiraIssue]:
        if max_results is not None:
            raise AssertionError("w3 collection must not be capped")
        if "resolved >=" in jql:
            if JiraIssueField.RESOLVED not in fields:
                raise AssertionError("resolutiondate is required")
            return [JiraIssue(
                key="TACEA-2",
                summary="해결 이슈",
                issue_type="개선",
                status="Closed",
                resolved="2026-07-15T12:30:00.000+0900",
            )]
        return [JiraIssue(
            key="TACEA-1",
            summary="생성 이슈",
            issue_type="개선",
            status="할 일",
            created="2026-02-15T09:00:00.000+0900",
        )]


class UnlimitedReviewJira:
    async def get_issues(self, jql: str, max_results: int | None, fields: frozenset[JiraIssueField]) -> list[JiraIssue]:
        if max_results is not None:
            raise AssertionError("w4 collection must not be capped")
        return []


class SemesterDashboardDataTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = QueryConfig(
            project_key="TACEA",
            issue_types=["인시던트", "개선"],
            active_statuses=[],
            closed_statuses=["Closed"],
            sla_threshold_days=30,
            year_start=2026,
        )
        self.queries = WidgetQueryBuilder(config).build(
            datetime.datetime(2026, 12, 31),
            week_start_override=datetime.datetime(2026, 1, 1),
        )

    async def test_resolution_fallback_uses_injected_time_and_keeps_status_breakdowns(self) -> None:
        class UnresolvedJira:
            async def get_issues(self, jql, max_results, fields):
                if max_results is not None:
                    raise AssertionError("Resolution collection must not be capped")
                return [
                    JiraIssue(issue_type="개선", status="할 일", created="2026-07-01T12:00:00+09:00"),
                    JiraIssue(issue_type="개선", status="할 일", created=""),
                ]

        result = await ResolutionCollector(
            UnresolvedJira(), self.queries,
            datetime.datetime(2026, 7, 2, 12, tzinfo=datetime.timezone(datetime.timedelta(hours=9))),
        ).collect()

        self.assertEqual(1, result.total)
        self.assertEqual(24, result.data.by_type["개선"].avg_hours)
        self.assertEqual(1, result.data.by_semester["h2"]["개선"].count)
        self.assertEqual(24, result.data.by_status_type["할 일"]["개선"].avg_hours)
        self.assertEqual(1, result.data.by_semester_status_type["h2"]["할 일"]["개선"].count)

    async def test_resolution_stats_are_split_by_semester_and_restored(self) -> None:
        result = await ResolutionCollector(
            ResolutionJira(),
            self.queries,
            datetime.datetime(2026, 12, 31),
        ).collect()

        self.assertEqual(2, result.data.by_type["인시던트"].count)
        self.assertEqual(1, result.data.by_semester["h1"]["인시던트"].count)
        self.assertEqual(1, result.data.by_semester["h2"]["인시던트"].count)
        self.assertEqual(1, result.data.by_status_type["할 일"]["인시던트"].count)
        self.assertEqual(1, result.data.by_semester_status_type["h2"]["Closed"]["인시던트"].count)

        restored = deserialize_widget(
            WidgetId.AVG_RESOLUTION_TYPE,
            serialize_widget(result),
        )
        restored_entry = restored.data.by_semester["h1"]["인시던트"]
        self.assertIsInstance(restored_entry, ResolutionTypeEntry)
        self.assertEqual(1, restored_entry.count)
        restored_status_entry = restored.data.by_semester_status_type["h2"]["Closed"]["인시던트"]
        self.assertIsInstance(restored_status_entry, ResolutionTypeEntry)

    async def test_resolved_details_use_resolution_date_for_period_filtering(self) -> None:
        result = await CreatedVsResolvedCollector(
            CreatedResolvedJira(),
            self.queries,
        ).collect()

        self.assertEqual("2026-02-15 09:00", result.data.created_details[0].created)
        self.assertEqual("2026-07-15 12:30", result.data.resolved_details[0].resolved)
        self.assertEqual("Closed", result.data.resolved_details[0].status)

    async def test_issue_review_details_can_be_collected_without_a_limit(self) -> None:
        result = await SimpleWithDetailsCollector(
            UnlimitedReviewJira(),
            "이슈 리뷰 중",
            self.queries.w4_issue_review(),
            datetime.datetime(2026, 12, 31),
            max_results=None,
        ).collect()

        self.assertEqual(0, result.total)
