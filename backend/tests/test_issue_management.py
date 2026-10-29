# backend/tests/test_issue_management.py
import asyncio
import pathlib
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.jira_port import JiraChartIssuePage, JiraIssue, JiraIssueField
from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot, IssueManagementSnapshotPort
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.domain.constants import KST
from src.domain.entities.widget_data import RecentIssueDetail
from src.presentation.api.v1.router import router


class IssueManagementTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = AsyncMock()
        self.jira.get_project_status_names.return_value = {}
        self.jira.get_issue_status_changes_batch.side_effect = lambda issues: {issue.key: [] for issue in issues}
        self.use_case = IssueManagementUseCase(self.jira)

    async def asyncTearDown(self):
        await self.use_case.aclose()

    async def refresh(self, issues):
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage(issues, False)
        self.use_case._last_attempt = float("-inf")
        snapshot = await self.use_case.list_issues()
        await self.use_case._task
        return snapshot, await self.use_case.list_issues()

    async def test_initial_load_includes_closed_and_deduplicates(self):
        initial, loaded = await self.refresh([
            JiraIssue(key="TACEA-1", status="Closed", created="2026-01-01T00:00:00+09:00"),
            JiraIssue(key="TACEA-2", status="처리 중"),
            JiraIssue(key="TACEA-2", status="결과 대기 중"),
        ])
        self.assertFalse(initial["initialized"])
        self.assertTrue(loaded["initialized"])
        self.assertEqual(2, len(loaded["issues"]))
        self.assertEqual({"Closed", "결과 대기 중"}, {issue.status for issue in loaded["issues"]})
        jql, limit, fields = self.jira.get_report_chart_issues.call_args.args
        self.assertIn('project = "TACEA"', jql)
        self.assertNotIn("status", jql)
        self.assertNotIn("updated >=", jql)
        self.assertIsNone(limit)
        self.assertIn(JiraIssueField.RECENT_TAC_ASSIGNEE, fields)

    async def test_incremental_append_and_status_update(self):
        await self.refresh([JiraIssue(key="TACEA-1"), JiraIssue(key="TACEA-2")])
        _, snapshot = await self.refresh([JiraIssue(key="TACEA-1", status="Closed"), JiraIssue(key="TACEA-3")])
        self.assertEqual(3, len(snapshot["issues"]))
        self.assertEqual("Closed", next(issue.status for issue in snapshot["issues"] if issue.key == "TACEA-1"))
        self.assertIn('updated >= "-', self.jira.get_report_chart_issues.call_args.args[0])

    async def test_repeated_snapshots_preserve_order_fields_and_response_isolation(self):
        _, loaded = await self.refresh([
            JiraIssue(key="TACEA-1", created="2026-01-01T00:00:00+09:00"),
            JiraIssue(key="TACEA-2", summary="원본", created="2026-02-01T00:00:00+09:00", qa_assignee="QA", recent_tac_assignee="TAC"),
            JiraIssue(key="TACEA-3", created="2026-02-01T00:00:00+09:00", assignee="지원"),
        ])
        repeated = await self.use_case.list_issues()
        self.assertEqual(loaded, repeated)
        self.assertEqual(["TACEA-3", "TACEA-2", "TACEA-1"], [issue.key for issue in repeated["issues"]])
        self.assertEqual("QA", repeated["issues"][1].tac_team)
        self.assertEqual("TAC", repeated["issues"][1].tac_assignee)
        loaded["issues"][1].summary = "변경"
        loaded["issues"].clear()
        next_snapshot = await self.use_case.list_issues()
        self.assertEqual(repeated, next_snapshot)
        self.assertEqual("원본", next_snapshot["issues"][1].summary)

    async def test_elapsed_days_advance_at_kst_midnight_without_jira_updates(self):
        await self.refresh([
            JiraIssue(key="TACEA-1", created="2026-10-05T14:59:00Z"),
            JiraIssue(key="TACEA-2", created="invalid"),
            JiraIssue(key="TACEA-3", created="2026-10-07T00:00:00+09:00"),
        ])
        with patch("src.application.use_cases.issue_management.datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 5, 23, 59, 59, tzinfo=KST)
            before = await self.use_case.list_issues()
            clock.now.return_value = datetime(2026, 10, 6, 0, 0, tzinfo=KST)
            after = await self.use_case.list_issues()
        before_by_key = {issue.key: issue for issue in before["issues"]}
        after_by_key = {issue.key: issue for issue in after["issues"]}
        self.assertEqual(0, before_by_key["TACEA-1"].elapsed_days)
        self.assertEqual(1, after_by_key["TACEA-1"].elapsed_days)
        self.assertEqual("2026-10-05 23:59", after_by_key["TACEA-1"].created)
        self.assertEqual(0, after_by_key["TACEA-2"].elapsed_days)
        self.assertEqual(0, after_by_key["TACEA-3"].elapsed_days)
        self.assertEqual(before["synced_at"], after["synced_at"])

    async def test_failed_refresh_preserves_details_and_updates_polling_state(self):
        _, loaded = await self.refresh([JiraIssue(key="TACEA-1", summary="원본")])
        started = asyncio.Event()
        finish = asyncio.Event()

        async def fail(*args):
            started.set()
            await finish.wait()
            raise RuntimeError("upstream")

        self.jira.get_report_chart_issues.side_effect = fail
        self.use_case._last_attempt = float("-inf")
        pending = await self.use_case.list_issues()
        await started.wait()
        self.assertTrue(pending["refreshing"])
        self.assertEqual(loaded["issues"], pending["issues"])
        finish.set()
        await self.use_case._task
        failed = await self.use_case.list_issues()
        self.assertFalse(failed["refreshing"])
        self.assertIsNotNone(failed["error"])
        self.assertEqual(loaded["issues"], failed["issues"])

    async def test_failed_partial_refresh_preserves_cache_and_cursor(self):
        await self.refresh([JiraIssue(key="TACEA-1")])
        synced_at = self.use_case._synced_at
        cursor = self.use_case._last_sync
        self.jira.get_report_chart_issues.side_effect = RuntimeError("upstream")
        self.use_case._last_attempt = float("-inf")
        await self.use_case.list_issues()
        await self.use_case._task
        snapshot = await self.use_case.list_issues()
        self.assertEqual(["TACEA-1"], [issue.key for issue in snapshot["issues"]])
        self.assertEqual(synced_at, snapshot["synced_at"])
        self.assertEqual(cursor, self.use_case._last_sync)
        self.assertIsNotNone(snapshot["error"])
        self.jira.get_report_chart_issues.side_effect = None
        _, recovered = await self.refresh([JiraIssue(key="TACEA-2")])
        self.assertIsNone(recovered["error"])
        self.assertEqual(2, len(recovered["issues"]))

    async def test_hourly_reconciliation_removes_deleted_issues(self):
        await self.refresh([JiraIssue(key="TACEA-1"), JiraIssue(key="TACEA-2")])
        self.use_case._last_full_sync -= 3601
        _, snapshot = await self.refresh([JiraIssue(key="TACEA-2")])
        self.assertEqual(["TACEA-2"], [issue.key for issue in snapshot["issues"]])
        self.assertNotIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])

    async def test_concurrent_requests_share_background_fetch_and_close_cancels(self):
        started = asyncio.Event()
        blocked = asyncio.Event()

        async def fetch(*args):
            started.set()
            await blocked.wait()
            return JiraChartIssuePage([], False)

        self.jira.get_report_chart_issues.side_effect = fetch
        results = await asyncio.gather(*(self.use_case.list_issues() for _ in range(10)))
        await started.wait()
        self.assertTrue(all(result["refreshing"] for result in results))
        self.assertEqual(1, self.jira.get_report_chart_issues.call_count)
        await self.use_case.aclose()
        self.assertTrue(self.use_case._task.cancelled())

    async def test_incomplete_snapshot_is_not_published(self):
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([JiraIssue(key="TACEA-1")], True)
        await self.use_case.list_issues()
        await self.use_case._task
        snapshot = await self.use_case.list_issues()
        self.assertFalse(snapshot["initialized"])
        self.assertEqual([], snapshot["issues"])
        self.assertIsNotNone(snapshot["error"])

    async def test_api_serializes_background_cache_without_http_caching(self):
        await self.refresh([JiraIssue(key="TACEA-1", status="Closed")])
        app = FastAPI()
        app.include_router(router)
        services = SimpleNamespace(auth=SimpleNamespace(enabled=False), issue_management=self.use_case)
        app.state.services = services
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/issue-management/issues")
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual("Closed", response.json()["issues"][0]["status"])
        self.assertTrue(response.json()["initialized"])

    async def test_api_requires_auth_when_login_enabled(self):
        app = FastAPI()
        app.include_router(router)
        services = SimpleNamespace(auth=SimpleNamespace(enabled=True), issue_management=self.use_case)
        app.state.services = services
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/issue-management/issues")
        self.assertEqual(401, response.status_code)
        self.jira.get_report_chart_issues.assert_not_called()


class IssueManagementPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = AsyncMock()
        self.jira.get_project_status_names.return_value = {}
        self.jira.get_issue_status_changes_batch.side_effect = lambda issues: {issue.key: [] for issue in issues}
        self.snapshots = AsyncMock(spec=IssueManagementSnapshotPort)
        now = datetime.now(KST)
        self.saved = IssueManagementSnapshot(
            (RecentIssueDetail("TACEA-1", "저장된 이슈", "개선", "처리 중", 4,
                               "2026-01-01T23:59:00+09:00", 0, reporter="보고자",
                               reporter_account_id="reporter-1"),),
            synced_at=now - timedelta(minutes=7), full_synced_at=now - timedelta(minutes=20),
            status_transitions={"TACEA-1": {}}, issue_updated_at={"TACEA-1": "2026-01-01T23:59:00+09:00"},
            transition_history_ready=True,
        )
        self.snapshots.load.return_value = self.saved
        self.snapshots.save.side_effect = lambda project, snapshot: snapshot
        self.use_case = IssueManagementUseCase(self.jira, snapshots=self.snapshots)
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([], False)

    async def asyncTearDown(self):
        await self.use_case.aclose()

    async def test_startup_restores_without_contacting_jira(self):
        await self.use_case.initialize()
        self.assertTrue(self.use_case._initialized)
        self.assertIsNone(self.use_case._task)
        self.jira.get_report_chart_issues.assert_not_called()
        self.snapshots.load.assert_awaited_once_with("TACEA")

    async def test_first_response_has_saved_rows_while_jira_is_blocked(self):
        blocked = asyncio.Event()
        async def fetch(*args):
            await blocked.wait()
            return JiraChartIssuePage([], False)

        self.jira.get_report_chart_issues.side_effect = fetch
        result = await asyncio.wait_for(self.use_case.list_issues(), 0.5)
        self.assertTrue(result["initialized"])
        self.assertTrue(result["refreshing"])
        self.assertEqual("저장된 이슈", result["issues"][0].summary)
        self.assertEqual(self.saved.synced_at.isoformat(), result["synced_at"])
        self.assertEqual("2026-01-01 23:59", result["issues"][0].created)
        self.assertGreater(result["issues"][0].elapsed_days, 0)

    async def test_concurrent_first_requests_restore_once(self):
        results = await asyncio.gather(*(self.use_case.list_issues() for _ in range(10)))
        await self.use_case._task
        self.snapshots.load.assert_awaited_once_with("TACEA")
        self.jira.get_report_chart_issues.assert_awaited_once()
        self.assertTrue(all(result["initialized"] for result in results))

    async def test_incremental_after_restart_covers_downtime_and_preserves_existing(self):
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([
            JiraIssue(key="TACEA-2", qa_assignee="QA", qa_assignee_account_id="qa-2",
                      recent_tac_assignee="TAC", recent_tac_assignee_account_id="tac-2",
                      personal_data_retrieved_at="2026-10-19T01:00:00Z"),
        ], False)
        await self.use_case.list_issues()
        await self.use_case._task
        result = await self.use_case.list_issues()
        jql = self.jira.get_report_chart_issues.call_args.args[0]
        minutes = int(jql.split('updated >= "-')[1].split('m"')[0])
        self.assertGreaterEqual(minutes, 9)
        self.assertLessEqual(minutes, 10)
        saved = self.snapshots.save.call_args.args[1]
        self.assertEqual(self.saved.full_synced_at, saved.full_synced_at)
        self.assertEqual({"TACEA-1", "TACEA-2"}, {row.key for row in result["issues"]})
        added = next(row for row in saved.issues if row.key == "TACEA-2")
        self.assertEqual(("QA", "qa-2", "TAC", "tac-2"),
                         (added.tac_team, added.tac_team_account_id, added.tac_assignee, added.tac_assignee_account_id))
        self.assertEqual("2026-10-19T01:00:00Z", added.personal_data_retrieved_at)

    async def test_old_full_snapshot_is_visible_until_reconciliation_finishes(self):
        self.snapshots.load.return_value = replace(self.saved, full_synced_at=datetime.now(KST) - timedelta(hours=2))
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([JiraIssue(key="TACEA-2")], False)
        initial = await self.use_case.list_issues()
        self.assertEqual("TACEA-1", initial["issues"][0].key)
        await self.use_case._task
        self.assertNotIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])
        result = await self.use_case.list_issues()
        self.assertEqual(["TACEA-2"], [row.key for row in result["issues"]])

    async def test_valid_empty_snapshot_is_initialized(self):
        self.snapshots.load.return_value = replace(self.saved, issues=())
        result = await self.use_case.list_issues()
        self.assertTrue(result["initialized"])
        self.assertEqual([], result["issues"])

    async def test_failed_save_keeps_last_snapshot_and_cursor(self):
        self.snapshots.save.side_effect = RuntimeError("unavailable")
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([JiraIssue(key="TACEA-2")], False)
        initial = await self.use_case.list_issues()
        cursor = self.use_case._last_sync
        await self.use_case._task
        failed = await self.use_case.list_issues()
        self.assertEqual(initial["issues"], failed["issues"])
        self.assertEqual(initial["synced_at"], failed["synced_at"])
        self.assertEqual(cursor, self.use_case._last_sync)
        self.assertIsNotNone(failed["error"])

    async def test_publishes_suppressed_repository_result(self):
        def save(project, snapshot):
            return replace(snapshot, issues=tuple(replace(row, reporter="개인정보 삭제") for row in snapshot.issues))

        self.snapshots.save.side_effect = save
        await self.use_case.list_issues()
        await self.use_case._task
        result = await self.use_case.list_issues()
        self.assertEqual("개인정보 삭제", result["issues"][0].reporter)

    async def test_cache_clear_cancels_refresh_and_restores_redacted_snapshot(self):
        started = asyncio.Event()

        async def blocked(*args):
            started.set()
            await asyncio.Event().wait()

        self.jira.get_report_chart_issues.side_effect = blocked
        await self.use_case.list_issues()
        await started.wait()
        pending = self.use_case._task
        await self.use_case.clear_personal_data_cache()
        self.assertTrue(pending.cancelled())
        self.snapshots.load.return_value = replace(self.saved, issues=(replace(self.saved.issues[0], reporter="개인정보 삭제"),))
        result = await self.use_case.list_issues()
        self.assertTrue(result["initialized"])
        self.assertEqual("개인정보 삭제", result["issues"][0].reporter)
        self.assertEqual(2, self.snapshots.load.await_count)
        self.snapshots.save.assert_not_awaited()

    async def test_unavailable_restore_can_recover_through_background_full_fetch(self):
        self.snapshots.load.side_effect = RuntimeError("temporary")
        self.jira.get_report_chart_issues.return_value = JiraChartIssuePage([JiraIssue(key="TACEA-2")], False)
        initial = await self.use_case.list_issues()
        self.assertFalse(initial["initialized"])
        await self.use_case._task
        result = await self.use_case.list_issues()
        self.assertTrue(result["initialized"])
        self.assertEqual("TACEA-2", result["issues"][0].key)
        self.assertNotIn("updated >=", self.jira.get_report_chart_issues.call_args.args[0])
