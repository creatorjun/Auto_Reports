# backend/tests/test_sla_enrichment_performance.py
import asyncio
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from src.infrastructure.external.sla_violation_jira_source import SlaViolationJiraSource
from test_sla_violation_jira_source import history_page, issue


_START = datetime(2026, 10, 1, tzinfo=ZoneInfo("Asia/Seoul"))
_END = datetime(2026, 11, 1, tzinfo=ZoneInfo("Asia/Seoul"))


class SlaEnrichmentPerformanceTest(unittest.IsolatedAsyncioTestCase):
    async def test_shared_asset_is_requested_once_per_refresh_and_not_retained(self):
        asset_calls = []
        started = asyncio.Event()
        release = asyncio.Event()
        candidates = [issue(f"TACEA-{index}", customfield_10859=[{
            "workspaceId": "workspace", "objectId": "42",
        }]) for index in range(5)]

        async def handler(request):
            if request.method == "POST":
                return httpx.Response(200, json={"issues": candidates, "isLast": True})
            if request.url.path.endswith("/changelog"):
                await asyncio.sleep(0)
                return httpx.Response(200, json=history_page())
            asset_calls.append(request.url.path)
            started.set()
            await release.wait()
            return httpx.Response(200, json={"label": f"파트너 {len(asset_calls)}"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                pending = asyncio.create_task(source.fetch_issues(_START, _END))
                await asyncio.wait_for(started.wait(), 1)
                for _ in range(10):
                    await asyncio.sleep(0)
                release.set()
                first = await pending
                self.assertEqual(1, len(asset_calls))
                self.assertEqual([("파트너 1",)] * 5, [entry.partners for entry in first])
                second = await source.fetch_issues(_START, _END)
                self.assertEqual(2, len(asset_calls))
                self.assertEqual([("파트너 2",)] * 5, [entry.partners for entry in second])

    async def test_next_issue_starts_before_slow_first_issue_finishes_and_order_is_preserved(self):
        release = asyncio.Event()
        sixth_started = asyncio.Event()
        candidates = [issue(f"TACEA-{index}") for index in range(12)]
        active = 0
        maximum = 0

        async def handler(request):
            nonlocal active, maximum
            if request.method == "POST":
                return httpx.Response(200, json={"issues": candidates, "isLast": True})
            key = request.url.path.split("/")[-2]
            active += 1
            maximum = max(maximum, active)
            try:
                if key == "TACEA-0":
                    await release.wait()
                elif key == "TACEA-5":
                    sixth_started.set()
                await asyncio.sleep(0)
                return httpx.Response(200, json=history_page())
            finally:
                active -= 1

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                pending = asyncio.create_task(source.fetch_issues(_START, _END))
                try:
                    await asyncio.wait_for(sixth_started.wait(), 0.3)
                finally:
                    release.set()
                    result = await pending
        self.assertEqual([entry["key"] for entry in candidates], [entry.key for entry in result])
        self.assertEqual(5, maximum)

    async def test_different_assets_are_resolved_concurrently(self):
        entered = set()
        all_started = asyncio.Event()
        release = asyncio.Event()
        candidates = [issue(f"TACEA-{index}", customfield_10859=[{
            "workspaceId": "workspace", "objectId": str(index),
        }]) for index in range(5)]

        async def handler(request):
            if request.method == "POST":
                return httpx.Response(200, json={"issues": candidates, "isLast": True})
            if request.url.path.endswith("/changelog"):
                return httpx.Response(200, json=history_page())
            identifier = request.url.path.rsplit("/", 1)[-1]
            entered.add(identifier)
            if len(entered) == 5:
                all_started.set()
            await release.wait()
            return httpx.Response(200, json={"label": identifier})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                pending = asyncio.create_task(source.fetch_issues(_START, _END))
                try:
                    await asyncio.wait_for(all_started.wait(), 1)
                finally:
                    release.set()
                    result = await pending
        self.assertEqual([(str(index),) for index in range(5)], [entry.partners for entry in result])

    async def test_close_drains_all_active_workers_and_does_not_start_waiting_issues(self):
        active = 0
        requested = []
        all_started = asyncio.Event()

        async def handler(request):
            nonlocal active
            if request.method == "POST":
                return httpx.Response(200, json={"issues": [issue(f"TACEA-{index}") for index in range(12)], "isLast": True})
            active += 1
            requested.append(request.url.path)
            if active == 5:
                all_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                active -= 1

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client)
            pending = asyncio.create_task(source.fetch_issues(_START, _END))
            await asyncio.wait_for(all_started.wait(), 1)
            await source.aclose()
            with self.assertRaises(asyncio.CancelledError):
                await pending
        self.assertEqual(0, active)
        self.assertEqual(5, len(requested))
        self.assertFalse(source._tasks)

    async def test_failed_worker_cancels_peers_and_next_refresh_can_retry(self):
        active = 0
        all_started = asyncio.Event()
        fail = True

        async def handler(request):
            nonlocal active
            if request.method == "POST":
                return httpx.Response(200, json={"issues": [issue(f"TACEA-{index}") for index in range(12)], "isLast": True})
            if not fail:
                return httpx.Response(200, json=history_page())
            active += 1
            if active == 5:
                all_started.set()
            try:
                if request.url.path.endswith("/TACEA-0/changelog"):
                    await all_started.wait()
                    return httpx.Response(503)
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                active -= 1

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                with self.assertRaisesRegex(RuntimeError, "Jira SLA violation request failed"):
                    await asyncio.wait_for(source.fetch_issues(_START, _END), 1)
                self.assertEqual(0, active)
                self.assertFalse(source._tasks)
                fail = False
                self.assertEqual(12, len(await source.fetch_issues(_START, _END)))

    async def test_canceling_shared_asset_waiters_releases_request_scope(self):
        started = asyncio.Event()
        active = 0
        canceled = 0
        candidates = [issue(f"TACEA-{index}", customfield_10859=[{
            "workspaceId": "workspace", "objectId": "42",
        }]) for index in range(5)]

        async def handler(request):
            nonlocal active, canceled
            if request.method == "POST":
                return httpx.Response(200, json={"issues": candidates, "isLast": True})
            if request.url.path.endswith("/changelog"):
                return httpx.Response(200, json=history_page())
            active += 1
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                canceled += 1
                raise
            finally:
                active -= 1

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                pending = asyncio.create_task(source.fetch_issues(_START, _END))
                await asyncio.wait_for(started.wait(), 1)
                pending.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await pending
                self.assertFalse(source._tasks)
        self.assertEqual(0, active)
        self.assertEqual(1, canceled)


if __name__ == "__main__":
    unittest.main()
