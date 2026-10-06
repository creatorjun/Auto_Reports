# backend/tests/test_issue_management.py
import asyncio
import pathlib
import sys
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.jira_port import JiraChartIssuePage, JiraIssue, JiraIssueField
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.domain.constants import KST
from src.presentation.api.v1.router import router


class IssueManagementTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = AsyncMock()
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
