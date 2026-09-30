# backend/tests/test_manual_refresh_cache.py
import asyncio
import unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI

from src.application.ports.jira_port import JiraAssetReference
from src.bootstrap.container import Container
from src.infrastructure.external.jira_client import JiraClient
from src.presentation.api.deps import get_audit, get_job_runner
from src.presentation.api.v1.trigger import router


class ManualRefreshCacheTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.jira = JiraClient("https://jira.example.test", "user", "token")
        await self.jira._client.aclose()
        self.requests = []
        self.version = 1

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request.url.path)
            if request.url.path.endswith("approximate-count"):
                return httpx.Response(200, json={"count": self.version})
            if "/object/" in request.url.path:
                return httpx.Response(200, json={"label": f"Partner {self.version}"})
            return httpx.Response(200, json={"issues": [{
                "key": f"T-{self.version}", "fields": {"summary": f"Issue {self.version}"},
            }]})

        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def asyncTearDown(self) -> None:
        await self.jira.aclose()

    async def test_forced_queries_ignore_warm_caches_and_inherit_in_child_tasks(self) -> None:
        methods = [
            self.jira.get_issues,
            self.jira.get_issues_with_sla,
            self.jira.get_issues_with_assignees,
            self.jira.get_redeployment_issues,
        ]
        for method in methods:
            self.assertEqual("T-1", (await method("project = T"))[0].key)
        self.assertEqual(1, await self.jira.get_issue_count("project = T"))
        self.version = 2
        before = len(self.requests)
        with self.jira.bypass_cache():
            results = await asyncio.gather(*(method("project = T") for method in methods))
            counts = await self.jira.get_issue_counts_batch(["project = T", "project = T"])
        self.assertTrue(all(result[0].key == "T-2" for result in results))
        self.assertEqual([2, 2], counts)
        self.assertEqual(before + 6, len(self.requests))
        for method in methods:
            self.assertEqual("T-1", (await method("project = T"))[0].key)
        self.assertEqual(1, await self.jira.get_issue_count("project = T"))
        self.assertEqual(before + 6, len(self.requests))

    async def test_normal_concurrent_request_does_not_inherit_forced_mode(self) -> None:
        await self.jira.get_issue_count("project = T")
        self.version = 2

        async def forced() -> int:
            with self.jira.bypass_cache():
                await asyncio.sleep(0)
                return await self.jira.get_issue_count("project = T")

        forced_count, normal_count = await asyncio.gather(
            forced(), self.jira.get_issue_count("project = T"),
        )
        self.assertEqual((2, 1), (forced_count, normal_count))

    async def test_forced_queries_do_not_wait_for_existing_inflight_requests(self) -> None:
        await self.jira.get_issue_count("project = T")
        await self.jira.get_issues("project = T", max_results=None)
        self.version = 2
        self.jira._count_cache._inflight["project = T"] = asyncio.get_running_loop().create_future()
        key = self.jira._issues_cache_key("project = T", None, ())
        self.jira._issues_cache._inflight[key] = asyncio.get_running_loop().create_future()
        with self.jira.bypass_cache():
            count, issues = await asyncio.wait_for(asyncio.gather(
                self.jira.get_issue_count("project = T"),
                self.jira.get_issues("project = T", max_results=None),
            ), timeout=1)
        self.assertEqual(2, count)
        self.assertEqual("T-2", issues[0].key)

    async def test_forced_asset_labels_bypass_cache(self) -> None:
        reference = JiraAssetReference("workspace", "1")
        labels = await self.jira.get_asset_object_labels([reference])
        self.assertEqual("Partner 1", labels[reference])
        self.version = 2
        with self.jira.bypass_cache():
            labels = await self.jira.get_asset_object_labels([reference])
        self.assertEqual("Partner 2", labels[reference])
        self.assertEqual(2, len(self.requests))

    async def test_failed_forced_queries_raise_and_restore_cache_mode(self) -> None:
        await self.jira.get_issue_count("project = T")
        await self.jira.get_issues("project = T")
        await self.jira._client.aclose()
        self.jira._client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(503)),
        )
        for query in (self.jira.get_issue_count, self.jira.get_issues):
            with self.assertRaises(RuntimeError):
                with self.jira.bypass_cache():
                    await query("project = T")
        self.assertEqual(1, await self.jira.get_issue_count("project = T"))
        self.assertEqual("T-1", (await self.jira.get_issues("project = T"))[0].key)

    async def test_container_applies_forced_mode_during_generation(self) -> None:
        container = Container.__new__(Container)
        container._jira = self.jira
        container._assembler = Mock()
        container._analyzer = Mock()
        container._cache = Mock()
        container._settings = Mock(report_retention_weeks=52)
        container._notify_todo = None
        container._notify_tac = None

        @asynccontextmanager
        async def session():
            yield Mock()

        container._database = Mock(session=session)
        await self.jira.get_issue_count("project = T")
        self.version = 2

        async def execute(**kwargs):
            return await self.jira.get_issue_count("project = T")

        with patch("src.bootstrap.container.GenerateReportUseCase") as use_case:
            use_case.return_value.execute = AsyncMock(side_effect=execute)
            self.assertEqual(2, await container.generate_report(bypass_jira_cache=True))
            self.assertEqual(1, await container.generate_report())

    async def test_manual_trigger_requests_jira_cache_bypass(self) -> None:
        runner = AsyncMock()
        audit = Mock()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_job_runner] = lambda: runner
        app.dependency_overrides[get_audit] = lambda: audit
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/trigger/", json={})
        self.assertEqual(202, response.status_code)
        runner.submit.assert_awaited_once_with(
            response.json()["job_id"], None, None, bypass_jira_cache=True,
        )
