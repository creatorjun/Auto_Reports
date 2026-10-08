# backend/tests/test_stage_duration.py
import asyncio
import datetime
import unittest

import httpx

from src.application.ports.jira_port import JiraIssue, JiraStatusChange
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_issue_metrics import resolution_elapsed
from src.application.services.stage_duration import stage_duration_hours
from src.application.widgets.resolution_collector import ResolutionCollector
from src.domain.entities.widget_data import StageDurationIssue
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class StageDurationTest(unittest.TestCase):
    def test_reentry_is_summed_once_per_issue_and_stops_at_resolution(self):
        changes = [
            JiraStatusChange("2026-01-02T00:00:00+09:00", "할 일", "구현 중"),
            JiraStatusChange("2026-01-03T00:00:00+09:00", "구현 중", "할 일"),
            JiraStatusChange("2026-01-04T00:00:00+09:00", "할 일", "구현 중"),
            JiraStatusChange("2026-01-05T00:00:00+09:00", "구현 중", "Closed"),
            JiraStatusChange("2026-01-06T00:00:00+09:00", "Closed", "재오픈"),
        ]
        actual = stage_duration_hours(
            "2026-01-01T00:00:00+09:00", "2026-01-05T00:00:00+09:00", "재오픈", list(reversed(changes)),
        )
        self.assertEqual({"할 일": 48, "구현 중": 48}, actual)
        self.assertEqual(96, sum(actual.values()))

    def test_timezone_offsets_and_no_transition_are_handled(self):
        self.assertEqual((1, 1), resolution_elapsed(
            "2026-01-01T00:00:00Z", "2026-01-01T10:00:00+09:00", datetime.datetime(2026, 1, 2),
        ))
        self.assertEqual({"구현 중": 1}, stage_duration_hours(
            "2026-01-01T00:00:00Z", "2026-01-01T10:00:00+09:00", "구현 중", [],
        ))
        self.assertEqual({}, stage_duration_hours(
            "2026-01-01T09:00:00", "2026-01-01T09:00:00", "Closed", [],
        ))

    def test_invalid_or_incomplete_history_cannot_produce_false_averages(self):
        with self.assertRaises(ValueError):
            stage_duration_hours("2026-01-02", "2026-01-01", "할 일", [])
        with self.assertRaises(ValueError):
            stage_duration_hours("2026-01-01", "2026-01-05", "Closed", [
                JiraStatusChange("2026-01-02", "할 일", "구현 중"),
                JiraStatusChange("2026-01-03", "자료 요청 중", "Closed"),
            ])


class StageHistoryAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = JiraClient("https://jira.example.test", "user", "token")
        await self.jira._client.aclose()
        self.requests = []
        self.responses = [
            {"startAt": 0, "total": 2, "isLast": False, "values": [{
                "created": "2026-01-02T00:00:00+0900",
                "items": [{"fieldId": "status", "fromString": "할 일", "toString": "구현 중"}],
            }]},
            {"startAt": 1, "total": 2, "isLast": True, "values": [{
                "created": "2026-01-03T00:00:00+0900",
                "items": [{"field": "status", "fromString": "구현 중", "toString": "Closed"}],
            }]},
        ]

        def handler(request):
            self.requests.append(request)
            return httpx.Response(200, json=self.responses[int(request.url.params["startAt"])])

        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def asyncTearDown(self):
        await self.jira.aclose()

    async def test_all_pages_are_mapped_cached_and_manual_refresh_bypasses_cache(self):
        changes = await self.jira.get_issue_status_changes("T-1")
        self.assertEqual(["구현 중", "Closed"], [change.to_status for change in changes])
        self.assertEqual(["0", "1"], [request.url.params["startAt"] for request in self.requests])
        self.assertEqual(changes, await self.jira.get_issue_status_changes("T-1"))
        self.assertEqual(2, len(self.requests))
        with self.jira.bypass_cache():
            self.assertEqual(changes, await self.jira.get_issue_status_changes("T-1"))
        self.assertEqual(4, len(self.requests))

    async def test_truncated_or_repeated_pages_fail(self):
        self.responses[0]["isLast"] = True
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            await self.jira.get_issue_status_changes("T-1")
        self.responses[0]["isLast"] = False
        self.responses[1]["startAt"] = 0
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            await self.jira.get_issue_status_changes("T-1")

    async def test_http_errors_propagate_without_empty_history(self):
        await self.jira._client.aclose()
        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
        with self.assertRaises(httpx.HTTPStatusError):
            await self.jira.get_issue_status_changes("T-1")


class StageDurationCollectorTest(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_history_is_excluded_without_losing_resolution_totals_or_later_batches(self):
        requested = []

        class Jira:
            async def get_issues(self, jql, max_results, fields):
                return [JiraIssue(
                    key=key, issue_type="개선", status="Closed",
                    created="2026-01-01", resolved="2026-01-04",
                ) for key in ("INVALID", "T-1", "T-2", "T-3", "T-4", "T-5")]

            async def get_issue_status_changes(self, issue_key):
                requested.append(issue_key)
                if issue_key == "INVALID":
                    return [
                        JiraStatusChange("2026-01-02", "할 일", "구현 중"),
                        JiraStatusChange("2026-01-03", "자료 요청 중", "Closed"),
                    ]
                await asyncio.sleep(0)
                return [JiraStatusChange("2026-01-02", "할 일", "Closed")]

        queries = WidgetQueryBuilder(QueryConfig("T", ["개선"], [], [], 30, 2026)).build(
            datetime.datetime(2026, 1, 4), week_start_override=datetime.datetime(2026, 1, 1),
        )
        with self.assertLogs("src.application.widgets.resolution_collector", level="WARNING") as logs:
            result = await ResolutionCollector(Jira(), queries, queries.week_end).collect()
        self.assertEqual(6, result.total)
        self.assertEqual(6, result.data.by_type["개선"].count)
        self.assertEqual(72, result.data.by_type["개선"].avg_hours)
        self.assertEqual(6, result.data.by_semester["h1"]["개선"].count)
        self.assertEqual(6, result.data.by_status_type["Closed"]["개선"].count)
        self.assertEqual(6, result.data.by_semester_status_type["h1"]["Closed"]["개선"].count)
        self.assertEqual(["T-1", "T-2", "T-3", "T-4", "T-5"], [issue.key for issue in result.data.stage_issues])
        self.assertTrue(all(issue.by_stage_hours == {"할 일": 24, "Closed": 48} for issue in result.data.stage_issues))
        self.assertEqual(["INVALID", "T-1", "T-2", "T-3", "T-4", "T-5"], requested)
        warning = "\n".join(logs.output)
        self.assertIn("INVALID", warning)
        self.assertIn("Issue status history is incomplete", warning)
        self.assertIn("구현 중", warning)
        self.assertIn("자료 요청 중", warning)
        restored = deserialize_widget(WidgetId.AVG_RESOLUTION_TYPE, serialize_widget(result))
        self.assertEqual(result.data.stage_issues, restored.data.stage_issues)

    async def test_invalid_stage_data_returns_empty_stages_without_fabricating_durations(self):
        cases = (
            ("2026-01-01", "2026-01-03", "Closed", [JiraStatusChange("invalid", "할 일", "Closed")], 1),
            ("invalid", "2026-01-03", "Closed", [], 0),
            ("2026-01-01", "2026-01-03", "", [], 1),
            ("2026-01-03", "2026-01-01", "Closed", [], 0),
        )
        queries = WidgetQueryBuilder(QueryConfig("T", ["개선"], [], [], 30, 2026)).build(datetime.datetime(2026, 1, 3))
        for created, resolved, status, changes, expected_total in cases:
            with self.subTest(created=created, resolved=resolved, status=status, changes=changes):
                class Jira:
                    async def get_issues(self, jql, max_results, fields):
                        return [JiraIssue(
                            key="INVALID", issue_type="개선", status=status, created=created, resolved=resolved,
                        )]

                    async def get_issue_status_changes(self, issue_key):
                        return changes

                with self.assertLogs("src.application.widgets.resolution_collector", level="WARNING"):
                    result = await ResolutionCollector(Jira(), queries, queries.week_end).collect()
                self.assertEqual(expected_total, result.total)
                self.assertEqual([], result.data.stage_issues)

    async def test_history_provider_value_error_is_not_treated_as_invalid_stage_data(self):
        class Jira:
            async def get_issues(self, jql, max_results, fields):
                return [JiraIssue(key="T-1", status="Closed", created="2026-01-01", resolved="2026-01-03")]

            async def get_issue_status_changes(self, issue_key):
                raise ValueError("invalid provider response")

        queries = WidgetQueryBuilder(QueryConfig("T", [], [], [], 30, 2026)).build(datetime.datetime(2026, 1, 3))
        with self.assertRaisesRegex(ValueError, "invalid provider response"):
            await ResolutionCollector(Jira(), queries, queries.week_end).collect()

    async def test_failed_history_cancels_other_requests_in_the_batch(self):
        cancelled = []

        class Jira:
            async def get_issues(self, jql, max_results, fields):
                return [JiraIssue(
                    key=key, status="Closed", created="2026-01-01", resolved="2026-01-03",
                ) for key in ("FAIL", "PENDING")]

            async def get_issue_status_changes(self, issue_key):
                if issue_key == "FAIL":
                    raise RuntimeError("history unavailable")
                try:
                    await asyncio.sleep(60)
                except asyncio.CancelledError:
                    cancelled.append(issue_key)
                    raise

        queries = WidgetQueryBuilder(QueryConfig("T", [], [], [], 30, 2026)).build(datetime.datetime(2026, 1, 3))
        with self.assertRaisesRegex(RuntimeError, "history unavailable"):
            await ResolutionCollector(Jira(), queries, queries.week_end).collect()
        self.assertEqual(["PENDING"], cancelled)

    async def test_collector_serializes_typed_stage_aggregates_and_supports_older_reports(self):
        class Jira:
            async def get_issues(self, jql, max_results, fields):
                return [JiraIssue(
                    key="T-1", issue_type="개선", status="Closed",
                    created="2026-01-01T00:00:00+09:00", resolved="2026-01-03T00:00:00+09:00",
                )]

            async def get_issue_status_changes(self, issue_key):
                return [JiraStatusChange("2026-01-02T00:00:00+09:00", "할 일", "Closed")]

        queries = WidgetQueryBuilder(QueryConfig("T", ["개선"], [], [], 30, 2026)).build(
            datetime.datetime(2026, 1, 3), week_start_override=datetime.datetime(2026, 1, 1),
        )
        result = await ResolutionCollector(Jira(), queries, queries.week_end).collect()
        restored = deserialize_widget(WidgetId.AVG_RESOLUTION_TYPE, serialize_widget(result))
        self.assertIsInstance(restored.data.stage_issues[0], StageDurationIssue)
        self.assertEqual({"할 일": 24, "Closed": 24}, restored.data.stage_issues[0].by_stage_hours)
        raw = serialize_widget(result)
        del raw["data"]["stage_issues"]
        self.assertIsNone(deserialize_widget(WidgetId.AVG_RESOLUTION_TYPE, raw).data.stage_issues)
