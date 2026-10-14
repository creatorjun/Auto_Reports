# backend/tests/test_redeployment_report.py
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from src.application.use_cases.redeployment_report import RedeploymentGenerationInProgress, RedeploymentReportUseCase
from src.domain.constants import KST
from src.domain.entities.redeployment_report import REDEPLOYMENT_START, RedeploymentReport, redeployment_refresh_due
from src.infrastructure.external.redeployment_jira_source import RedeploymentJiraSource
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.deps import get_audit, get_auth
from src.presentation.api.v1.deps import get_redeployment_use_case
from src.presentation.api.v1.router import router

NOW = datetime(2026, 10, 14, 8, tzinfo=KST)


def sample_report(at=NOW):
    return RedeploymentReport(1, REDEPLOYMENT_START, at, "schedule", "project = TACEA", ())


def issue(key="TACEA-1", closed=True, **custom):
    return {"key": key, "fields": {
        "summary": "재배포 검증", "issuetype": {"name": "인시던트"},
        "status": {"id": "6" if closed else "10001", "name": "닫힘" if closed else "결과 대기 중"},
        "created": "2025-12-01T00:00:00+0900", "resolutiondate": "2026-02-09T10:00:00+0900" if closed else None,
        "customfield_12421": {"value": "2026-01"}, "customfield_11885": {"value": "개발오류"},
        "customfield_11852": "파일 누락\n재패치", "customfield_11753": 2, "customfield_10859": [], **custom,
    }}


class RedeploymentUseCaseTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.source = AsyncMock()
        self.source.fetch.return_value = ("query", (), ())
        self.repo = AsyncMock()
        self.repo.try_generation_lock.return_value = True
        self.repo.get_latest.return_value = None
        self.repo.save.side_effect = lambda report: replace(report, id=3)
        self.use_case = RedeploymentReportUseCase(self.source, self.repo, clock=lambda: NOW)

    async def test_first_generation_saves_snapshot(self):
        result = await self.use_case.generate("schedule")
        self.assertEqual((3, REDEPLOYMENT_START, NOW), (result.id, result.period_start, result.generated_at))
        self.source.fetch.assert_awaited_once_with(NOW)
        self.repo.save.assert_awaited_once()

    async def test_restart_skips_fresh_snapshot_but_manual_refresh_runs(self):
        self.repo.get_latest.return_value = sample_report()
        self.assertEqual(sample_report(), await self.use_case.generate("schedule"))
        self.source.fetch.assert_not_awaited()
        await self.use_case.generate("admin", force=True)
        self.source.fetch.assert_awaited_once()

    async def test_previous_day_is_refreshed_at_eight(self):
        self.repo.get_latest.return_value = sample_report(NOW - timedelta(days=1))
        await self.use_case.generate("schedule")
        self.repo.save.assert_awaited_once()

    async def test_provider_failure_preserves_stored_snapshot(self):
        self.repo.get_latest.return_value = sample_report(NOW - timedelta(days=1))
        self.source.fetch.side_effect = RuntimeError("Jira unavailable")
        with self.assertRaises(RuntimeError):
            await self.use_case.generate("schedule")
        self.repo.save.assert_not_awaited()

    async def test_lock_prevents_duplicate_fetch_and_save(self):
        self.repo.try_generation_lock.return_value = False
        with self.assertRaises(RedeploymentGenerationInProgress):
            await self.use_case.generate("admin", force=True)
        self.source.fetch.assert_not_awaited()
        self.repo.save.assert_not_awaited()

    def test_kst_boundary_and_timezone_independence(self):
        self.assertEqual(NOW - timedelta(days=1), redeployment_refresh_due(NOW - timedelta(seconds=1)))
        self.assertEqual(NOW, redeployment_refresh_due(NOW.astimezone(timezone.utc)))
        scheduler = create_scheduler("0 9 * * mon", "UTC", AsyncMock(), refresh_redeployments=AsyncMock())
        job = scheduler.get_job("redeployment_daily")
        self.assertEqual(NOW, job.trigger.get_next_fire_time(None, NOW - timedelta(seconds=1)))
        self.assertEqual(NOW + timedelta(days=1), job.trigger.get_next_fire_time(NOW, NOW))
        self.assertEqual(1, job.max_instances)
        self.assertTrue(job.coalesce)
        self.assertIsNotNone(job.next_run_time)


class RedeploymentSourceTest(unittest.IsolatedAsyncioTestCase):
    async def fetch(self, handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = RedeploymentJiraSource("https://jira.test", "user", "token", "TACEA", client)
            result = await source.fetch(NOW)
            await source.aclose()
            self.assertFalse(client.is_closed)
            return result

    async def test_all_pages_and_original_fields_are_preserved(self):
        calls = []
        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            if body.get("nextPageToken") == "page2":
                return httpx.Response(200, json={"issues": [issue("TACEA-2", False, customfield_11753=None)], "isLast": True})
            return httpx.Response(200, json={"issues": [issue()], "isLast": False, "nextPageToken": "page2"})
        jql, tickets, warnings = await self.fetch(handler)
        self.assertEqual(2, len(calls))
        self.assertIn('resolved >= "2026-01-01"', jql)
        self.assertIn('OR status != Closed', jql)
        self.assertNotIn('created >=', jql)
        self.assertEqual((True, False), tuple(ticket.closed for ticket in tickets))
        self.assertEqual("2026-01", tickets[0].completion_month)
        self.assertEqual("파일 누락\n재패치", tickets[0].reason)
        self.assertIsNone(tickets[1].repatch_count)
        self.assertEqual((), warnings)

    async def test_incomplete_pagination_and_http_failure_do_not_return_partial_data(self):
        for payload in ({"issues": [issue()], "isLast": False}, {"issues": [issue()]}):
            with self.subTest(payload=payload):
                with self.assertRaises(RuntimeError):
                    await self.fetch(lambda request: httpx.Response(200, json=payload))
        with self.assertRaises(RuntimeError):
            await self.fetch(lambda request: httpx.Response(429, json={}))

    async def test_asset_failure_is_explicit_not_head_office(self):
        def handler(request):
            if request.method == "GET":
                return httpx.Response(403)
            return httpx.Response(200, json={"isLast": True, "issues": [issue(customfield_10859=[{"workspaceId": "workspace", "objectId": "123"}])]})
        _, tickets, warnings = await self.fetch(handler)
        self.assertEqual(("이름 확인 불가 (객체 123)",), tickets[0].partners)
        self.assertEqual(1, len(warnings))

    async def test_invalid_count_is_unknown_and_zero_is_preserved(self):
        for value, expected in ((0, 0), (-1, None), (1.5, None), (True, None), ("2", None), (None, None)):
            with self.subTest(value=value):
                _, tickets, _ = await self.fetch(lambda request: httpx.Response(200, json={"isLast": True, "issues": [issue(customfield_11753=value)]}))
                self.assertEqual(expected, tickets[0].repatch_count)

    async def test_invalid_required_date_aborts_snapshot(self):
        with self.assertRaises(RuntimeError):
            await self.fetch(lambda request: httpx.Response(200, json={"isLast": True, "issues": [issue(created="invalid")]}))


class RedeploymentApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_auth_snapshot_generation_conflict_and_failure(self):
        app = FastAPI()
        app.include_router(router)
        use_case = AsyncMock(spec=RedeploymentReportUseCase)
        use_case.get_latest.return_value = sample_report()
        use_case.generate.return_value = sample_report()
        audit = Mock()
        app.dependency_overrides[get_redeployment_use_case] = lambda: use_case
        app.dependency_overrides[get_audit] = lambda: audit
        app.dependency_overrides[get_auth] = lambda: SimpleNamespace(enabled=True, decode_access_token=lambda token: "tester")
        headers = {"Authorization": "Bearer test"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for method, suffix in (("GET", "/latest"), ("POST", "")):
                self.assertEqual(401, (await client.request(method, "/api/v1/redeployments" + suffix)).status_code)
            latest = await client.get("/api/v1/redeployments/latest", headers=headers)
            self.assertEqual("2026-01-01", latest.json()["period_start"])
            self.assertEqual("no-store", latest.headers["cache-control"])
            created = await client.post("/api/v1/redeployments", headers=headers)
            self.assertEqual(200, created.status_code, created.text)
            use_case.generate.assert_awaited_once_with("tester", force=True)
            audit.record.assert_called_once_with("REDEPLOYMENT_REPORT_CREATE", report_id=1, ticket_count=0)
            for error, status in ((RedeploymentGenerationInProgress(), 409), (RuntimeError("provider failed"), 502)):
                use_case.generate.side_effect = error
                response = await client.post("/api/v1/redeployments", headers=headers)
                self.assertEqual(status, response.status_code)
