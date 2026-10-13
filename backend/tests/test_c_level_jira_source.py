# backend/tests/test_c_level_jira_source.py
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone

import httpx

from src.infrastructure.external.c_level_jira_source import CLevelJiraSource


_EARLIEST = datetime(2026, 8, 1, tzinfo=timezone.utc)
_AS_OF = datetime(2026, 10, 13, tzinfo=timezone.utc)
_REGISTRY = [{"id": "10104", "statuses": [
    {"id": "1", "name": "할 일", "statusCategory": {"key": "new"}},
    {"id": "2", "name": "이슈 리뷰 중", "statusCategory": {"key": "indeterminate"}},
    {"id": "3", "name": "완료", "statusCategory": {"key": "done"}},
]}]


def issue(key: str = "TACEA-1") -> dict:
    return {"key": key, "fields": {
        "summary": "시험 이슈", "created": "2026-07-01T09:00:00+0900",
        "updated": "2026-10-13T12:00:00+0900",
        "issuetype": {"id": "10104", "name": "서비스 요청"},
        "status": {"id": "2", "name": "이슈 리뷰 중", "statusCategory": {"key": "indeterminate"}},
        "customfield_11022": "고객 A", "customfield_10854": None,
        "customfield_10859": [{"label": "파트너 A"}],
        "customfield_12522": {"displayName": "TAC 담당"},
        "reporter": {"displayName": "보고자"}, "assignee": {"displayName": "담당자"},
        "customfield_12152": {"completedCycles": [{
            "startTime": {"iso8601": "2026-07-01T09:00:00+0900"},
            "stopTime": {"iso8601": "2026-07-01T12:00:00+0900"},
            "goalDuration": {"millis": 14400000}, "elapsedTime": {"millis": 10800000},
            "remainingTime": {"millis": 3600000}, "breached": False,
        }]},
        "customfield_12151": {"completedCycles": [], "ongoingCycle": {
            "startTime": {"iso8601": "2026-07-01T09:00:00+0900"},
            "breachTime": {"iso8601": "2026-07-03T09:00:00+0900"},
            "goalDuration": {"millis": 28800000}, "elapsedTime": {"millis": 36000000},
            "remainingTime": {"millis": -7200000}, "breached": True, "paused": True,
        }},
        "customfield_12454": "2026-07-01T12:00:00+0900",
        "customfield_12051": {"value": "고객 확인 대기"},
        "customfield_12018": {"value": "고객"},
    }}


def history(identifier: str, created: str, items: list[dict]) -> dict:
    return {"id": identifier, "created": created, "items": items}


class CLevelJiraSourceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.issues = [issue()]
        self.histories: dict[str, list[dict]] = {}
        self.requests: list[httpx.Request] = []
        self.override = None
        self.now = 1.0
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        self.source = CLevelJiraSource(
            "https://company.atlassian.net", "user", "token",
            client=self.client, clock=lambda: self.now,
        )

    async def asyncTearDown(self) -> None:
        await self.source.aclose()
        await self.client.aclose()

    async def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.override is not None:
            response = await self.override(request)
            if response is not None:
                return response
        if request.url.path.endswith("/statuses"):
            return httpx.Response(200, json=_REGISTRY)
        if request.url.path.endswith("/search/jql"):
            return httpx.Response(200, json={"issues": self.issues, "isLast": True})
        if request.url.path.endswith("/changelog"):
            key = request.url.path.split("/")[-2]
            values = self.histories.get(key, [])
            return httpx.Response(200, json={"values": values, "startAt": 0, "total": len(values), "isLast": True})
        if "/v1/object/" in request.url.path:
            return httpx.Response(200, json={"label": "Assets 고객"})
        if "/rest/api/3/status/" in request.url.path:
            return httpx.Response(404)
        raise AssertionError(f"Unexpected request: {request.url.path}")

    async def test_maps_current_fields_and_preserves_raw_sla_cycles(self) -> None:
        values = await self.source.fetch_issues(_EARLIEST, _AS_OF)
        value = values[0]
        self.assertEqual("고객 A", value.customer_name)
        self.assertEqual(("파트너 A",), value.partner_names)
        self.assertEqual("TAC 담당", value.tac_assignee)
        self.assertEqual("고객 확인 대기", value.jira_delay_reason)
        self.assertEqual("고객", value.jira_delay_responsibility)
        self.assertIsNotNone(value.first_response_at)
        self.assertEqual(2, len(value.sla_cycles))
        self.assertFalse(value.sla_cycles[0].breached)
        self.assertTrue(value.sla_cycles[1].breached)
        self.assertTrue(value.sla_cycles[1].paused)
        self.assertEqual(-7200000, value.sla_cycles[1].remaining_ms)
        search = next(request for request in self.requests if request.method == "POST")
        jql = json.loads(search.content)["jql"]
        self.assertIn("status CHANGED AFTER", jql)
        self.assertIn("OR resolved >=", jql)
        self.assertIn("issuetype in (10104, 10105, 10110)", jql)

    async def test_fetches_all_history_pages_and_keeps_deleted_status_unknown(self) -> None:
        records = [
            history("1", "2026-07-02T00:00:00Z", [{"fieldId": "status", "from": "1", "fromString": "할 일", "to": "99", "toString": "삭제된 상태"}]),
            history("2", "2026-07-03T00:00:00Z", [{"fieldId": "status", "from": "99", "fromString": "삭제된 상태", "to": "2", "toString": "이슈 리뷰 중"}]),
        ]

        async def override(request: httpx.Request):
            if request.url.path.endswith("/changelog"):
                index = int(request.url.params["startAt"])
                return httpx.Response(200, json={"values": records[index:index + 1], "startAt": index, "total": 2, "isLast": index == 1})
            return None

        self.override = override
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual(2, len(value.status_changes))
        self.assertEqual("", value.status_changes[0].to_status.category)
        self.assertEqual("new", value.status_changes[0].from_status.category)
        self.assertTrue(value.history_complete)
        self.assertTrue(any("완료 범주" in warning for warning in value.warnings))

    async def test_reconstructs_customer_and_user_dimensions_before_cutoff(self) -> None:
        self.histories["TACEA-1"] = [history("1", "2026-10-14T00:00:00Z", [
            {"fieldId": "customfield_11022", "fromString": "이전 고객", "toString": "고객 A"},
            {"fieldId": "customfield_12522", "fromString": "이전 TAC", "toString": "TAC 담당"},
            {"fieldId": "customfield_10859", "from": "123", "fromString": "이전 파트너", "toString": "파트너 A"},
        ])]
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual("이전 고객", value.customer_name)
        self.assertEqual("이전 TAC", value.tac_assignee)
        self.assertEqual(("이전 파트너",), value.partner_names)
        self.assertEqual("customer_name", value.field_changes[0].field_id)

    async def test_legacy_status_category_is_loaded_by_id_once_across_issues(self) -> None:
        self.issues = [issue("TACEA-1"), issue("TACEA-2")]
        for value in self.issues:
            self.histories[value["key"]] = [history("1", "2026-07-02T00:00:00Z", [
                {"fieldId": "status", "from": "10205", "fromString": "QA 검토 중", "to": "2", "toString": "이슈 리뷰 중"},
            ])]

        async def override(request: httpx.Request):
            if request.url.path == "/rest/api/3/status/10205":
                return httpx.Response(200, json={"id": "10205", "name": "QA 검토 중", "statusCategory": {"key": "indeterminate"}})
            return None

        self.override = override
        values = await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertTrue(all(value.status_changes[0].from_status.category == "indeterminate" for value in values))
        self.assertFalse(any("완료 범주" in warning for value in values for warning in value.warnings))
        self.assertEqual(1, sum(request.url.path == "/rest/api/3/status/10205" for request in self.requests))
        await self.source.fetch_issues(_EARLIEST, _AS_OF + timedelta(days=1))
        self.assertEqual(1, sum(request.url.path == "/rest/api/3/status/10205" for request in self.requests))

    async def test_legacy_status_api_failure_is_not_treated_as_deleted(self) -> None:
        self.histories["TACEA-1"] = [history("1", "2026-07-02T00:00:00Z", [
            {"fieldId": "status", "from": "10205", "fromString": "QA 검토 중", "to": "2", "toString": "이슈 리뷰 중"},
        ])]

        async def override(request: httpx.Request):
            if request.url.path == "/rest/api/3/status/10205":
                return httpx.Response(503)
            return None

        self.override = override
        with self.assertRaisesRegex(RuntimeError, "Jira C-Level collection failed"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

    async def test_ambiguous_historical_assets_are_not_reported_as_current_names(self) -> None:
        self.histories["TACEA-1"] = [history("1", "2026-10-14T00:00:00Z", [
            {"fieldId": "customfield_10859", "from": "1,2", "fromString": "A, B", "toString": "파트너 A"},
        ])]
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual((), value.partner_names)
        self.assertTrue(any("과거 명칭" in warning for warning in value.warnings))

    async def test_unknown_historical_customer_text_does_not_fall_back_to_current_asset(self) -> None:
        self.issues[0]["fields"]["customfield_10854"] = [{"label": "현재 Assets 고객"}]
        self.histories["TACEA-1"] = [history("1", "2026-10-14T00:00:00Z", [
            {"fieldId": "customfield_11022", "from": "unknown", "fromString": None, "toString": "고객 A"},
        ])]
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual("", value.customer_name)
        self.assertTrue(any("기준일 이전 값" in warning for warning in value.warnings))

    async def test_invalid_history_time_marks_history_and_dimensions_unknown(self) -> None:
        self.histories["TACEA-1"] = [history("1", "bad", [{"fieldId": "status", "from": "1", "to": "2"}])]
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertFalse(value.history_complete)
        self.assertEqual("", value.customer_name)
        self.assertEqual("", value.tac_assignee)

    async def test_absent_sla_is_not_inferred_from_first_response_date(self) -> None:
        del self.issues[0]["fields"]["customfield_12152"]
        self.issues[0]["fields"]["customfield_12151"]["ongoingCycle"]["breached"] = None
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual(1, len(value.sla_cycles))
        self.assertIsNone(value.sla_cycles[0].breached)
        self.assertIsNotNone(value.first_response_at)
        self.assertTrue(any("initial_response" in warning for warning in value.warnings))

    async def test_asset_lookup_is_cached_but_explicit_refresh_reloads(self) -> None:
        fields = self.issues[0]["fields"]
        fields["customfield_11022"] = None
        fields["customfield_10854"] = [{"workspaceId": "space", "objectId": "42"}]
        value = (await self.source.fetch_issues(_EARLIEST, _AS_OF))[0]
        self.assertEqual("Assets 고객", value.customer_name)
        await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertEqual(1, sum("/v1/object/" in str(request.url) for request in self.requests))
        await self.source.fetch_issues(_EARLIEST, _AS_OF, refresh=True)
        self.assertEqual(2, sum("/v1/object/" in str(request.url) for request in self.requests))

    async def test_http_failures_are_propagated_without_empty_fallback(self) -> None:
        async def override(request: httpx.Request):
            if request.url.path.endswith("/changelog"):
                return httpx.Response(503)
            return None

        self.override = override
        with self.assertRaisesRegex(RuntimeError, "Jira C-Level collection failed"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertEqual(0, len(self.source._cache))
        self.assertEqual(0, len(self.source._tasks))

    async def test_malformed_json_and_transport_errors_use_provider_neutral_boundary(self) -> None:
        async def invalid_json(request: httpx.Request):
            if request.url.path.endswith("/statuses"):
                return httpx.Response(200, text="not-json")
            return None

        self.override = invalid_json
        with self.assertRaisesRegex(RuntimeError, "^Jira C-Level collection failed$") as malformed:
            await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertIsInstance(malformed.exception.__cause__, json.JSONDecodeError)

        async def timeout(request: httpx.Request):
            raise httpx.ReadTimeout("provider detail", request=request)

        self.override = timeout
        with self.assertRaisesRegex(RuntimeError, "^Jira C-Level collection failed$") as timed_out:
            await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertIsInstance(timed_out.exception.__cause__, httpx.ReadTimeout)

    async def test_asset_permission_failure_is_propagated(self) -> None:
        self.issues[0]["fields"]["customfield_10859"] = [{"workspaceId": "space", "objectId": "42"}]

        async def override(request: httpx.Request):
            if "/v1/object/" in request.url.path:
                return httpx.Response(403)
            return None

        self.override = override
        with self.assertRaisesRegex(RuntimeError, "Jira C-Level collection failed"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

    async def test_search_repeated_token_and_truncated_history_raise(self) -> None:
        async def repeated(request: httpx.Request):
            if request.method == "POST":
                payload = json.loads(request.content)
                index = 2 if "nextPageToken" in payload else 1
                return httpx.Response(200, json={"issues": [issue(f"TACEA-{index}")], "nextPageToken": "again", "isLast": False})
            return None

        self.override = repeated
        with self.assertRaisesRegex(RuntimeError, "pagination repeated"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

        async def truncated(request: httpx.Request):
            if request.url.path.endswith("/changelog"):
                return httpx.Response(200, json={"values": [], "startAt": 0, "total": 1, "isLast": True})
            return None

        self.override = truncated
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

    async def test_search_paginates_and_excludes_issues_created_at_cutoff(self) -> None:
        future = issue("TACEA-2")
        future["fields"]["created"] = _AS_OF.isoformat()

        async def override(request: httpx.Request):
            if request.method == "POST":
                payload = json.loads(request.content)
                if "nextPageToken" in payload:
                    return httpx.Response(200, json={"issues": [future], "isLast": True})
                return httpx.Response(200, json={"issues": self.issues, "nextPageToken": "second", "isLast": False})
            return None

        self.override = override
        values = await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertEqual(["TACEA-1"], [value.key for value in values])
        self.assertEqual(1, sum(request.url.path.endswith("/changelog") for request in self.requests))

    async def test_ttl_and_report_cache_entry_bound(self) -> None:
        await self.source.fetch_issues(_EARLIEST, _AS_OF)
        count = len(self.requests)
        await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertEqual(count, len(self.requests))
        self.now = 122
        await self.source.fetch_issues(_EARLIEST, _AS_OF)
        self.assertGreater(len(self.requests), count)
        for days in range(10):
            await self.source.fetch_issues(_EARLIEST, _AS_OF + timedelta(days=days))
        self.assertEqual(8, len(self.source._cache))

    async def test_history_cache_reused_across_periods_and_invalidated_by_updated(self) -> None:
        await self.source.fetch_issues(_EARLIEST, _AS_OF)
        await self.source.fetch_issues(_EARLIEST, _AS_OF + timedelta(days=1))
        self.assertEqual(1, sum(request.url.path.endswith("/changelog") for request in self.requests))
        self.issues[0]["fields"]["updated"] = "2026-10-14T00:00:00Z"
        await self.source.fetch_issues(_EARLIEST, _AS_OF + timedelta(days=2))
        self.assertEqual(2, sum(request.url.path.endswith("/changelog") for request in self.requests))
        await self.source.fetch_issues(_EARLIEST, _AS_OF + timedelta(days=2), refresh=True)
        self.assertEqual(3, sum(request.url.path.endswith("/changelog") for request in self.requests))

    async def test_history_total_change_between_pages_requires_retry(self) -> None:
        async def override(request: httpx.Request):
            if request.url.path.endswith("/changelog"):
                index = int(request.url.params["startAt"])
                values = [history(str(index), "2026-07-02T00:00:00Z", [])]
                return httpx.Response(200, json={"values": values, "startAt": index, "total": 2 + index})
            return None

        self.override = override
        with self.assertRaisesRegex(RuntimeError, "changed during collection"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

    async def test_failure_cancels_sibling_tasks_and_concurrency_is_bounded(self) -> None:
        self.issues = [issue(f"TACEA-{index}") for index in range(1, 13)]
        started = 0
        active = 0
        maximum = 0
        reached = asyncio.Event()

        async def override(request: httpx.Request):
            nonlocal started, active, maximum
            if not request.url.path.endswith("/changelog"):
                return None
            active += 1
            started += 1
            maximum = max(maximum, active)
            if started == 6:
                reached.set()
            try:
                await reached.wait()
                if request.url.path.endswith("/TACEA-1/changelog"):
                    return httpx.Response(503)
                await asyncio.Future()
            finally:
                active -= 1

        self.override = override
        with self.assertRaisesRegex(RuntimeError, "Jira C-Level collection failed"):
            await asyncio.wait_for(self.source.fetch_issues(_EARLIEST, _AS_OF), timeout=2)
        self.assertEqual(6, maximum)
        self.assertEqual(0, active)
        self.assertEqual(0, len(self.source._tasks))

    async def test_close_cancels_active_requests_and_preserves_injected_client_ownership(self) -> None:
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def override(request: httpx.Request):
            if request.url.path.endswith("/changelog"):
                started.set()
                try:
                    await asyncio.Future()
                finally:
                    stopped.set()
            return None

        self.override = override
        task = asyncio.create_task(self.source.fetch_issues(_EARLIEST, _AS_OF))
        await asyncio.wait_for(started.wait(), timeout=2)
        await self.source.aclose()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(stopped.is_set())
        self.assertFalse(self.client.is_closed)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await self.source.fetch_issues(_EARLIEST, _AS_OF)

    async def test_context_manager_closes_owned_client(self) -> None:
        source = CLevelJiraSource("https://company.atlassian.net", "user", "token")
        async with source:
            self.assertFalse(source._client.is_closed)
        self.assertTrue(source._client.is_closed)

    async def test_invalid_period_is_rejected_before_network(self) -> None:
        with self.assertRaises(ValueError):
            await self.source.fetch_issues(datetime(2026, 1, 1), _AS_OF)
        with self.assertRaises(ValueError):
            await self.source.fetch_issues(_AS_OF, _EARLIEST)
        self.assertEqual([], self.requests)
