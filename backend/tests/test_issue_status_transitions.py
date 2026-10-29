# backend/tests/test_issue_status_transitions.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot, IssueManagementSnapshotPort
from src.application.ports.jira_port import JiraChartIssuePage, JiraIssue, JiraPort, JiraStatusChange
from src.application.services.issue_status_transitions import latest_status_transitions, status_transition_days
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.domain.constants import KST
from src.domain.entities.widget_data import RecentIssueDetail

NOW = datetime(2026, 10, 29, 10, tzinfo=KST)
CLOSED = "2026-10-28T10:50:52.051000+09:00"


class IssueStatusTransitionDatesTest(unittest.TestCase):
    def test_latest_entry_is_sorted_by_instant_and_localized_by_status_id(self):
        changes = [
            JiraStatusChange(CLOSED, "결과 대기 중", "Closed", "6", "7"),
            JiraStatusChange("2026-04-23T15:03:03+09:00", "결과 대기 중", "Closed", "6", "7"),
            JiraStatusChange("2026-10-29T01:00:00Z", "Closed", "재 오픈", "8", "6"),
        ]
        result = latest_status_transitions(changes, {"6": "닫힘", "8": "재 오픈"})
        self.assertEqual(CLOSED, result["닫힘"])
        self.assertEqual("2026-10-29T10:00:00+09:00", result["재 오픈"])
        self.assertNotIn("Closed", result)
        self.assertEqual({"닫힘": 1, "재 오픈": 0}, status_transition_days({"TACEA-3340": result}, NOW)["TACEA-3340"])

    def test_kst_calendar_dates_include_midnight_and_do_not_use_24_hour_duration(self):
        transitions = {"TACEA-1": {"닫힘": "2026-10-28T14:59:59Z", "재 오픈": "2026-10-28T15:00:00Z"}}
        result = status_transition_days(transitions, datetime(2026, 10, 28, 15, 0, 1, tzinfo=timezone.utc))
        self.assertEqual({"닫힘": 1, "재 오픈": 0}, result["TACEA-1"])

    def test_no_history_does_not_invent_initial_status_or_creation_date(self):
        self.assertEqual({}, latest_status_transitions([], {"1": "할 일"}))
        self.assertEqual({"TACEA-1": {}}, status_transition_days({"TACEA-1": {}}, NOW))

    def test_same_status_history_item_does_not_reset_entry_date(self):
        changes = [
            JiraStatusChange(CLOSED, "결과 대기 중", "Closed", "6", "7"),
            JiraStatusChange("2026-10-29T01:00:00Z", "Closed", "닫힘", "6", "6"),
        ]
        self.assertEqual({"닫힘": CLOSED}, latest_status_transitions(changes, {"6": "닫힘"}))

    def test_invalid_and_timezone_missing_dates_are_not_zero_day_matches(self):
        for value in ("invalid", "", "2026-10-28", "2026-10-28T10:00:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                latest_status_transitions([JiraStatusChange(value, "할 일", "닫힘")], {})
        with self.assertRaises(ValueError):
            latest_status_transitions([JiraStatusChange(CLOSED, "할 일", "")], {})


class IssueManagementStatusTransitionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = AsyncMock(spec=JiraPort)
        self.jira.get_project_status_names.return_value = {"6": "닫힘", "8": "재 오픈"}
        self.histories = {"TACEA-3340": [JiraStatusChange(CLOSED, "결과 대기 중", "Closed", "6", "7")]}
        self.jira.get_issue_status_changes_batch.side_effect = lambda issues: {issue.key: self.histories.get(issue.key, []) for issue in issues}
        self.use_case = IssueManagementUseCase(self.jira)
        self.issue = JiraIssue(key="TACEA-3340", issue_id="32968", status="닫힘", status_id="6", created="2025-09-08T16:40:11+09:00", updated=CLOSED)

    async def asyncTearDown(self):
        await self.use_case.aclose()

    async def refresh(self, issues):
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage(issues, False)
        self.use_case._last_attempt = float("-inf")
        await self.use_case.list_issues()
        await self.use_case._task
        with patch("src.application.use_cases.issue_management.datetime") as clock:
            clock.now.return_value = NOW
            return await self.use_case.list_issues()

    async def test_response_preserves_creation_age_and_exposes_independent_history_age(self):
        result = await self.refresh([self.issue])
        self.assertTrue(result["transition_history_ready"])
        self.assertEqual(416, result["issues"][0].elapsed_days)
        self.assertEqual({"닫힘": 1}, result["status_transition_days"][self.issue.key])
        self.assertEqual({"닫힘": CLOSED}, result["status_transitions"][self.issue.key])

    async def test_reopened_issue_still_has_latest_closed_transition(self):
        self.histories[self.issue.key] += [JiraStatusChange("2026-10-29T09:00:00+09:00", "Closed", "재 오픈", "8", "6")]
        result = await self.refresh([replace(self.issue, status="재 오픈", status_id="8")])
        self.assertEqual("재 오픈", result["issues"][0].status)
        self.assertEqual({"닫힘": 1, "재 오픈": 0}, result["status_transition_days"][self.issue.key])

    async def test_hourly_full_sync_reuses_unchanged_history_and_drops_deleted_keys(self):
        other = replace(self.issue, key="TACEA-2", issue_id="2")
        await self.refresh([self.issue, other])
        self.use_case._last_full_sync -= 3601
        result = await self.refresh([self.issue])
        self.jira.get_issue_status_changes_batch.assert_awaited_once()
        self.assertEqual({self.issue.key}, set(result["status_transitions"]))
        self.assertNotIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])

    async def test_incremental_update_fetches_only_changed_issue_and_resets_latest_transition(self):
        other = replace(self.issue, key="TACEA-2", issue_id="2")
        await self.refresh([self.issue, other])
        self.histories[self.issue.key] += [JiraStatusChange("2026-10-29T09:00:00+09:00", "재 오픈", "Closed", "6", "8")]
        updated = replace(self.issue, updated="2026-10-29T09:00:00+09:00")
        result = await self.refresh([updated, other])
        self.jira.get_issue_status_changes_batch.assert_awaited_with([updated])
        self.assertEqual(0, result["status_transition_days"][self.issue.key]["닫힘"])
        self.assertIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])

    async def test_failed_history_fetch_keeps_previous_rows_dates_and_cursor(self):
        previous = await self.refresh([self.issue])
        cursor = self.use_case._last_sync
        self.jira.get_issue_status_changes_batch.side_effect = RuntimeError("upstream")
        failed = await self.refresh([replace(self.issue, updated="2026-10-29T09:00:00+09:00")])
        self.assertEqual(previous["issues"], failed["issues"])
        self.assertEqual(previous["status_transitions"], failed["status_transitions"])
        self.assertEqual(previous["synced_at"], failed["synced_at"])
        self.assertEqual(cursor, self.use_case._last_sync)
        self.assertIsNotNone(failed["error"])

    async def test_incomplete_batch_is_not_published_as_empty_history(self):
        self.jira.get_issue_status_changes_batch.side_effect = lambda issues: {}
        result = await self.refresh([self.issue])
        self.assertFalse(result["initialized"])
        self.assertFalse(result["transition_history_ready"])
        self.assertEqual({}, result["status_transitions"])
        self.assertIsNotNone(result["error"])

    async def test_history_response_isolation_and_midnight_recalculation(self):
        result = await self.refresh([self.issue])
        result["status_transitions"][self.issue.key]["닫힘"] = "invalid"
        result["status_transition_days"][self.issue.key]["닫힘"] = 999
        with patch("src.application.use_cases.issue_management.datetime") as clock:
            clock.now.return_value = NOW + timedelta(days=1)
            following = await self.use_case.list_issues()
        self.assertEqual(CLOSED, following["status_transitions"][self.issue.key]["닫힘"])
        self.assertEqual(2, following["status_transition_days"][self.issue.key]["닫힘"])

    async def test_legacy_snapshot_is_returned_immediately_and_forces_full_enrichment(self):
        snapshots = AsyncMock(spec=IssueManagementSnapshotPort)
        snapshots.load.return_value = IssueManagementSnapshot(
            (RecentIssueDetail(self.issue.key, "원본", "인시던트", "닫힘", 0, self.issue.created, 0),), NOW, NOW,
        )
        snapshots.save.side_effect = lambda project, snapshot: snapshot
        await self.use_case.aclose()
        self.use_case = IssueManagementUseCase(self.jira, snapshots=snapshots)
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([self.issue], False)
        first = await self.use_case.list_issues()
        self.assertTrue(first["initialized"])
        self.assertFalse(first["transition_history_ready"])
        self.assertEqual("원본", first["issues"][0].summary)
        await self.use_case._task
        result = await self.use_case.list_issues()
        self.assertTrue(result["transition_history_ready"])
        self.assertNotIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])
        self.assertTrue(snapshots.save.call_args.args[1].transition_history_ready)

    async def test_close_cancels_inflight_bulk_history_and_does_not_publish(self):
        started = asyncio.Event()

        async def blocked(issues):
            started.set()
            await asyncio.Event().wait()

        self.jira.get_issue_status_changes_batch.side_effect = blocked
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([self.issue], False)
        await self.use_case.list_issues()
        await started.wait()
        await self.use_case.aclose()
        self.assertTrue(self.use_case._task.cancelled())
        self.assertFalse(self.use_case._transition_history_ready)
        self.assertFalse(self.use_case._initialized)
