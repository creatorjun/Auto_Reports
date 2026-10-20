# backend/tests/test_sla_digest_jira_source.py
import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from src.infrastructure.external.sla_digest_jira_source import SlaDigestJiraSource


def catalog(*identifiers: str) -> list[dict]:
    return [
        {"id": identifier, "name": f"단계 {identifier}", "schema": {
            "type": "sd-servicelevelagreement", "custom": "com.atlassian.servicedesk:sd-sla-field",
        }}
        for identifier in identifiers or ("customfield_10001", "customfield_10002")
    ]


def cycle(goal: int = 100000, remaining: int = 30000, **overrides: object) -> dict:
    return {
        "paused": False, "breached": remaining < 0,
        "goalDuration": {"millis": goal}, "remainingTime": {"millis": remaining},
        "elapsedTime": {"millis": goal - remaining}, **overrides,
    }


def issue(key: str = "TACEA-1", **overrides: object) -> dict:
    return {"key": key, "fields": {
        "summary": "서버 로그 점검", "status": {"name": "이슈 리뷰 중"},
        "assignee": {"displayName": "담당자"}, "issuetype": {"name": "인시던트"},
        "customfield_10001": {"ongoingCycle": cycle()},
        "customfield_10002": None, **overrides,
    }}


class SlaDigestJiraSourceTest(unittest.IsolatedAsyncioTestCase):
    async def collect(self, handler, **kwargs) -> tuple:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaDigestJiraSource("https://jira.example.com/", "user", "token", client=client, **kwargs) as source:
                return await source.fetch_entries()

    def handler(self, issues: list[dict], fields: object = None):
        def respond(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=catalog() if fields is None else fields)
            return httpx.Response(200, json={"issues": issues, "isLast": True})
        return respond

    async def test_discovers_all_sla_fields_and_paginates_all_unfinished_tickets_without_dates(self) -> None:
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=[
                    {"id": "summary", "name": "Summary", "schema": {"type": "string"}},
                    *catalog("customfield_10001", "customfield_10002", "customfield_10003"),
                ])
            body = json.loads(request.content)
            requests.append(body)
            self.assertEqual(100, body["maxResults"])
            self.assertIn('project = "TACEA"', body["jql"])
            self.assertIn("statusCategory != Done", body["jql"])
            self.assertNotIn("created", body["jql"])
            self.assertEqual(
                ["summary", "status", "assignee", "issuetype", "customfield_10001", "customfield_10002", "customfield_10003"],
                body["fields"],
            )
            if "nextPageToken" not in body:
                return httpx.Response(200, json={
                    "issues": [issue(customfield_10003=None)], "isLast": False, "nextPageToken": "page-2",
                })
            self.assertEqual("page-2", body["nextPageToken"])
            return httpx.Response(200, json={"issues": [issue("TACEA-2", customfield_10003={
                "ongoingCycle": cycle(remaining=20000),
            })], "isLast": True})

        entries = await self.collect(handler)
        self.assertEqual(2, len(requests))
        self.assertEqual(["TACEA-1", "TACEA-2", "TACEA-2"], [entry.key for entry in entries])
        self.assertEqual("customfield_10003", entries[-1].sla_id)
        self.assertEqual("단계 customfield_10003", entries[-1].sla_name)
        self.assertEqual(("서버 로그 점검", "이슈 리뷰 중", "담당자"), (entries[0].summary, entries[0].status, entries[0].assignee))

    async def test_preserves_paused_breached_and_all_ongoing_cycles_without_filtering_by_status(self) -> None:
        entries = await self.collect(self.handler([
            issue(customfield_10001={"ongoingCycle": cycle(paused=True)}, customfield_10002={
                "ongoingCycle": cycle(remaining=-10000), "completedCycles": [{"breached": True}],
            }),
        ]))
        self.assertEqual(2, len(entries))
        self.assertTrue(entries[0].paused)
        self.assertFalse(entries[0].breached)
        self.assertTrue(entries[1].breached)
        self.assertEqual(-10000, entries[1].remaining_millis)
        self.assertTrue(all(entry.issue_has_breached_sla for entry in entries))

    async def test_completed_breach_marks_all_ongoing_stages_on_that_ticket(self) -> None:
        entries = await self.collect(self.handler([
            issue(customfield_10002={"completedCycles": [{"breached": True}], "ongoingCycle": None}),
            issue("TACEA-2", customfield_10001={
                "completedCycles": [{"breached": True}], "ongoingCycle": cycle(remaining=20000),
            }, customfield_10002={"ongoingCycle": cycle()}),
            issue("TACEA-3", customfield_10002={"completedCycles": [{"breached": False}]}),
        ]))
        self.assertEqual(["TACEA-1", "TACEA-2", "TACEA-2", "TACEA-3"], [entry.key for entry in entries])
        self.assertEqual([True, True, True, False], [entry.issue_has_breached_sla for entry in entries])
        self.assertTrue(all(not entry.breached for entry in entries))

    async def test_nullable_and_empty_cycles_leave_the_issue_breach_marker_false(self) -> None:
        entries = await self.collect(self.handler([
            issue(customfield_10001={"completedCycles": None, "ongoingCycle": cycle()}, customfield_10002=None),
            issue("TACEA-2", customfield_10001={"completedCycles": [], "ongoingCycle": cycle()}, customfield_10002={
                "completedCycles": None, "ongoingCycle": None,
            }),
            issue("TACEA-3", customfield_10002={"completedCycles": [], "ongoingCycle": None}),
        ]))
        self.assertEqual(3, len(entries))
        self.assertTrue(all(not entry.issue_has_breached_sla for entry in entries))

    async def test_breached_zero_goal_still_marks_other_ongoing_stages_on_that_ticket(self) -> None:
        with self.assertLogs("src.infrastructure.external.sla_digest_jira_source", level="WARNING"):
            entries = await self.collect(self.handler([
                issue(customfield_10002={"ongoingCycle": cycle(0, -1)}),
            ]))
        self.assertEqual(1, len(entries))
        self.assertTrue(entries[0].issue_has_breached_sla)

    async def test_broken_completed_cycle_shapes_and_breach_flags_fail_closed(self) -> None:
        for completed in ("invalid", {}, [None], [[]], [{}], [{"breached": "true"}], [{"breached": 1}]):
            with self.subTest(completed=completed):
                with self.assertRaises(RuntimeError):
                    await self.collect(self.handler([
                        issue(customfield_10002={"completedCycles": completed}),
                    ]))

    async def test_ignores_nonapplicable_completed_cycles_and_license_aliases(self) -> None:
        entries = await self.collect(self.handler([
            issue("TACEA-1", customfield_10001=None, customfield_10002={"completedCycles": [{"breached": True}]}),
            issue("TACEA-2", customfield_10001={}, customfield_10002={"completedCycles": [], "ongoingCycle": None}),
            *(issue(f"TACEA-{index}", issuetype={"name": name}) for index, name in enumerate(
                ("라이선스", "라이센스", "라이선스 요청", "라이센스 요청", " 라이센스 "), start=3,
            )),
            issue("TACEA-8", status={"name": "Closed", "statusCategory": {"key": "done"}}),
        ]))
        self.assertEqual((), entries)

    async def test_keeps_unassigned_tickets(self) -> None:
        entries = await self.collect(self.handler([issue(assignee=None)]))
        self.assertEqual("미지정", entries[0].assignee)

    async def test_deduplicates_tickets_across_pages(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=catalog())
            if "nextPageToken" not in json.loads(request.content):
                return httpx.Response(200, json={"issues": [issue()], "nextPageToken": "second"})
            return httpx.Response(200, json={"issues": [issue(), issue("TACEA-2")], "isLast": True})

        self.assertEqual(["TACEA-1", "TACEA-2"], [entry.key for entry in await self.collect(handler)])

    async def test_duplicate_ticket_uses_latest_cycle_and_breach_facts(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=catalog())
            if "nextPageToken" not in json.loads(request.content):
                return httpx.Response(200, json={
                    "issues": [issue(), issue("TACEA-2")], "nextPageToken": "second",
                })
            return httpx.Response(200, json={"issues": [
                issue(customfield_10002={"completedCycles": [{"breached": True}]}),
                issue("TACEA-2", customfield_10001={"completedCycles": [{"breached": True}]}),
            ], "isLast": True})

        entries = await self.collect(handler)
        self.assertEqual(1, len(entries))
        self.assertEqual("TACEA-1", entries[0].key)
        self.assertTrue(entries[0].issue_has_breached_sla)

    async def test_refreshes_field_catalog_and_ticket_values_on_every_fetch(self) -> None:
        counts = {"/rest/api/3/field": 0, "/rest/api/3/search/jql": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            counts[request.url.path] += 1
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=catalog())
            return httpx.Response(200, json={"issues": [issue(customfield_10001={
                "ongoingCycle": cycle(remaining=30000 // counts[request.url.path]),
            })], "isLast": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaDigestJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                self.assertEqual(30000, (await source.fetch_entries())[0].remaining_millis)
                self.assertEqual(15000, (await source.fetch_entries())[0].remaining_millis)
        self.assertEqual([2, 2], list(counts.values()))

    async def test_zero_goal_is_skipped_with_a_warning(self) -> None:
        with self.assertLogs("src.infrastructure.external.sla_digest_jira_source", level="WARNING") as logs:
            entries = await self.collect(self.handler([issue(customfield_10001={"ongoingCycle": cycle(0, 0)})]))
        self.assertEqual((), entries)
        self.assertIn("zero-duration SLA goal", logs.output[0])

    async def test_missing_or_invalid_issue_fields_fail_the_whole_fetch(self) -> None:
        candidates = [None, {}, {"key": ""}, {"key": "TACEA-2", "fields": None}]
        for field in ("summary", "status", "assignee", "issuetype", "customfield_10001", "customfield_10002"):
            candidate = issue("TACEA-2")
            del candidate["fields"][field]
            candidates.append(candidate)
        candidates.extend(issue("TACEA-2", **values) for values in (
            {"summary": ""}, {"status": {"name": ""}}, {"assignee": {}}, {"issuetype": []},
            {"customfield_10001": "invalid"}, {"customfield_10001": {"completedCycles": "invalid"}},
        ))
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    await self.collect(self.handler([issue(), candidate]))

    async def test_invalid_timing_or_cycle_flags_fail_the_whole_fetch(self) -> None:
        candidates = [[], "invalid"]
        candidates.extend(cycle(**values) for values in (
            {"paused": "true"}, {"breached": 0}, {"goalDuration": {"millis": -1}},
            {"goalDuration": {"millis": True}}, {"goalDuration": {"millis": 1.5}},
            {"remainingTime": {"millis": "30000"}}, {"remainingTime": {"millis": False}},
            {"remainingTime": {"millis": 100001}}, {"elapsedTime": {"millis": -1}},
            {"elapsedTime": {"millis": 50000}}, {"elapsedTime": None},
            {"breached": True}, {"remainingTime": None},
        ))
        for field in ("paused", "breached", "goalDuration", "remainingTime"):
            candidate = cycle()
            del candidate[field]
            candidates.append(candidate)
        candidates.append(cycle(remaining=-1, breached=False))
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    await self.collect(self.handler([issue(), issue("TACEA-2", customfield_10001={"ongoingCycle": candidate})]))

    async def test_elapsed_time_is_optional_and_zero_remaining_can_be_breached_or_unbreached(self) -> None:
        ongoing = cycle(remaining=0)
        del ongoing["elapsedTime"]
        entries = await self.collect(self.handler([
            issue(customfield_10001={"ongoingCycle": ongoing}, customfield_10002={
                "ongoingCycle": cycle(remaining=0, breached=True),
            }),
        ]))
        self.assertEqual(2, len(entries))

    async def test_invalid_or_empty_field_catalog_fails_closed(self) -> None:
        invalid_fields = [
            {}, [], [None], [{"id": "summary", "schema": {"type": "string"}}],
            [{**catalog()[0], "id": "summary"}], [{**catalog()[0], "name": ""}],
            [catalog()[0], {**catalog()[0], "name": "충돌"}],
        ]
        for fields in invalid_fields:
            with self.subTest(fields=fields):
                with self.assertRaises(RuntimeError):
                    await self.collect(self.handler([], fields))

    async def test_invalid_truncated_and_repeated_pagination_fail_closed(self) -> None:
        invalid_pages = [
            [], {}, {"issues": {}}, {"issues": [issue()]},
            {"issues": [issue()], "isLast": True, "nextPageToken": "unexpected"},
            {"issues": [issue()], "isLast": True, "nextPageToken": []},
            {"issues": [issue()], "isLast": "true", "nextPageToken": "second"},
            {"issues": [issue()], "isLast": 0, "nextPageToken": "second"},
            {"issues": [issue()], "nextPageToken": 1},
            {"issues": [issue()], "nextPageToken": " "},
            {"issues": [], "nextPageToken": "second"},
            {"issues": [issue()], "nextPageToken": "repeated"},
        ]
        for page in invalid_pages:
            def handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json=catalog() if request.url.path.endswith("/field") else page)

            with self.subTest(page=page):
                with self.assertRaises(RuntimeError):
                    await self.collect(handler)

    async def test_http_and_json_errors_propagate_without_partial_results(self) -> None:
        for response in (
            httpx.Response(403, json={"error": "forbidden"}),
            httpx.Response(429, json={"error": "rate limited"}),
            httpx.Response(500), httpx.Response(200, content=b"not json"),
        ):
            def handler(request: httpx.Request) -> httpx.Response:
                if request.url.path.endswith("/field"):
                    return httpx.Response(200, json=catalog())
                if "nextPageToken" not in json.loads(request.content):
                    return httpx.Response(200, json={"issues": [issue()], "nextPageToken": "second"})
                return response

            with self.subTest(status=response.status_code):
                with self.assertRaises(RuntimeError):
                    await self.collect(handler)

    async def test_request_timeout_is_finite_even_with_injected_client(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertTrue(all(value is not None and value > 0 for value in request.extensions["timeout"].values()))
            return httpx.Response(200, json=catalog() if request.url.path.endswith("/field") else {"issues": [], "isLast": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=None) as client:
            async with SlaDigestJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                self.assertEqual((), await source.fetch_entries())

    async def test_source_respects_injected_client_ownership_and_rejects_use_after_close(self) -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(self.handler([]))) as client:
            source = SlaDigestJiraSource("https://jira.example.com", "user", "token", client=client)
            await source.aclose()
            await source.aclose()
            self.assertFalse(client.is_closed)
            with self.assertRaises(RuntimeError):
                await source.fetch_entries()

    async def test_context_manager_closes_owned_client_on_failure(self) -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
        with patch("src.infrastructure.external.sla_digest_jira_source.httpx.AsyncClient", return_value=client):
            with self.assertRaises(RuntimeError):
                async with SlaDigestJiraSource("https://jira.example.com", "user", "token") as source:
                    await source.fetch_entries()
        self.assertTrue(client.is_closed)

    async def test_close_cancels_inflight_fetch_and_keeps_injected_client_open(self) -> None:
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = SlaDigestJiraSource("https://jira.example.com", "user", "token", client=client)
            task = asyncio.create_task(source.fetch_entries())
            await asyncio.wait_for(started.wait(), timeout=1)
            await asyncio.wait_for(source.aclose(), timeout=1)
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(cancelled.is_set())
            self.assertFalse(client.is_closed)

    async def test_caller_cancellation_does_not_leak_request_or_prevent_next_fetch(self) -> None:
        started = asyncio.Event()
        cancelled = asyncio.Event()
        calls = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise
            return httpx.Response(200, json=catalog() if request.url.path.endswith("/field") else {"issues": [], "isLast": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaDigestJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                task = asyncio.create_task(source.fetch_entries())
                await asyncio.wait_for(started.wait(), timeout=1)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertTrue(cancelled.is_set())
                self.assertEqual((), await source.fetch_entries())

    def test_rejects_unsafe_project_keys_before_constructing_http_client(self) -> None:
        with self.assertRaises(ValueError):
            SlaDigestJiraSource("https://jira.example.com", "user", "token", project_key='TACEA" OR project = OTHER')
