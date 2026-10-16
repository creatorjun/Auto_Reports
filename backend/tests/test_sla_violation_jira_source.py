# backend/tests/test_sla_violation_jira_source.py
import asyncio
import json
import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from src.application.services.sla_violation_metrics import build_sla_violation_report
from src.infrastructure.external.sla_violation_jira_source import SlaViolationJiraSource


_KST = ZoneInfo("Asia/Seoul")
_START = datetime(2026, 10, 1, tzinfo=_KST)
_END = datetime(2026, 11, 1, tzinfo=_KST)


def issue(key: str = "TACEA-1", **overrides: object) -> dict:
    return {
        "key": key,
        "fields": {
            "summary": "[서울 교통공사] MF2 컴포넌트 개선의 건",
            "created": "2026-10-01T00:00:00+09:00",
            "status": {"name": "결과 대기 중"},
            "reporter": {"displayName": "김영준 과장"},
            "assignee": {"displayName": "조장희 수석"},
            "customfield_12522": [{"displayName": "한준희 선임"}],
            "customfield_11022": "서울교통공사",
            "customfield_10859": [],
            "customfield_12152": {"completedCycles": [{"breached": True}]},
            "customfield_12151": None,
            **overrides,
        },
    }


def history(identifier: str, created: str, previous: str, current: str) -> dict:
    return {
        "id": identifier,
        "created": created,
        "items": [{"fieldId": "status", "fromString": previous, "toString": current}],
    }


def history_page(values: list[dict] | None = None, start: int = 0, total: int = 0) -> dict:
    return {"values": values or [], "startAt": start, "total": total}


class SlaViolationJiraSourceTest(unittest.IsolatedAsyncioTestCase):
    async def collect(self, handler, **kwargs) -> tuple:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client, **kwargs) as source:
                return await source.fetch_issues(_START, _END)

    async def test_paginates_all_types_and_applies_exact_creation_boundaries(self) -> None:
        searches = []
        histories = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                payload = json.loads(request.content)
                searches.append(payload)
                if "nextPageToken" not in payload:
                    return httpx.Response(200, json={
                        "issues": [
                            issue("TACEA-0", created="2026-09-30T14:59:59+00:00"),
                            issue("TACEA-1", created="2026-09-30T15:00:00+00:00"),
                        ],
                        "nextPageToken": "second", "isLast": False,
                    })
                return httpx.Response(200, json={
                    "issues": [
                        issue("TACEA-2", created="2026-10-31T14:59:59Z", issuetype={"name": "새 요청 유형"}),
                        issue("TACEA-3", created="2026-10-31T15:00:00Z"),
                        issue("TACEA-4", customfield_12152={"completedCycles": [{"breached": False}]}),
                    ], "isLast": True,
                })
            histories.append(request.url.path)
            return httpx.Response(200, json=history_page())

        result = await self.collect(handler)
        self.assertEqual(["TACEA-1", "TACEA-2"], [item.key for item in result])
        self.assertEqual(2, len(histories))
        self.assertEqual("second", searches[1]["nextPageToken"])
        self.assertNotIn("issuetype", searches[0]["jql"].lower())
        self.assertNotIn("status", searches[0]["jql"].lower())
        self.assertIn("issuetype", searches[0]["fields"])
        self.assertEqual([None, "새 요청 유형"], [item.issue_type for item in result])

    async def test_missing_or_empty_issue_type_remains_unknown(self) -> None:
        candidates = [issue(f"TACEA-{index}", issuetype=value) for index, value in enumerate((None, {}, {"name": " "}))]

        def handler(request: httpx.Request) -> httpx.Response:
            data = {"issues": candidates, "isLast": True} if request.url.path.endswith("/search/jql") else history_page()
            return httpx.Response(200, json=data)

        self.assertTrue(all(item.issue_type is None for item in await self.collect(handler)))

    async def test_retains_each_metric_and_exact_breach_time_with_full_history(self) -> None:
        requested_starts = []
        breach = datetime(2026, 10, 2, 3, tzinfo=timezone.utc)
        candidate = issue(
            customfield_12152={"completedCycles": [
                {"breached": False},
                {"breached": True, "breachTime": {"epochMillis": int(breach.timestamp() * 1000)}},
                {"breached": True, "startTime": {"iso8601": "2026-10-03T09:00:00+0900"}, "goalDuration": {"millis": 3600000}},
            ]},
            customfield_12151={"ongoingCycle": {"breached": True, "breachTime": {"jira": "2026-10-04T09:00:00.000+0900"}}},
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                return httpx.Response(200, json={"issues": [candidate], "isLast": True})
            start = int(request.url.params["startAt"])
            requested_starts.append(start)
            values = [history("1", "2026-10-02T00:00:00+09:00", "할 일", "연구소 검토 중")] if start == 0 else [
                history("2", "2026-10-03T00:00:00+09:00", "연구소 검토 중", "결과 대기 중"),
            ]
            return httpx.Response(200, json=history_page(values, start, 2))

        result = (await self.collect(handler))[0]
        self.assertEqual([0, 1], requested_starts)
        self.assertEqual(["initial_response", "initial_response", "initial_response", "resolution"], [cycle.metric for cycle in result.cycles])
        self.assertFalse(result.cycles[0].breached)
        self.assertEqual(breach, result.cycles[1].breached_at)
        self.assertIsNone(result.cycles[2].breached_at)
        self.assertEqual(datetime(2026, 10, 4, tzinfo=timezone.utc), result.cycles[3].breached_at)
        self.assertTrue(result.history_complete)
        self.assertEqual(2, len(result.changes))
        self.assertEqual("서울교통공사", result.customer)
        self.assertEqual((), result.partners)
        self.assertEqual("김영준 과장", result.reporter)
        self.assertEqual("조장희 수석", result.assignee)
        self.assertEqual("한준희 선임", result.tac_assignee)
        self.assertIn("최초응답 SLA 위반 시각 확인 불가", result.warnings)

    async def test_preserves_contract_goals_and_each_cycle_without_wall_clock_time(self) -> None:
        started = {"iso8601": "2026-10-01T00:00:00+09:00"}
        stopped = {"iso8601": "2026-10-10T00:00:00+09:00"}
        deadline = {"iso8601": "2026-10-02T00:00:00+09:00"}
        candidates = [
            issue("TACEA-1", customfield_12152={"completedCycles": [{
                "breached": False, "startTime": started, "stopTime": stopped,
                "breachTime": deadline, "goalDuration": {"millis": 14400000},
                "elapsedTime": {"millis": 3600000}, "remainingTime": {"millis": 10800000},
            }]}, customfield_12151={"completedCycles": [{
                "breached": True, "startTime": started, "stopTime": stopped,
                "breachTime": deadline, "goalDuration": {"millis": 144000000},
                "elapsedTime": {"millis": 151200000}, "remainingTime": {"millis": -7200000},
            }], "ongoingCycle": {
                "breached": True, "startTime": stopped, "paused": True,
                "breachTime": deadline, "goalDuration": {"millis": 432000000},
                "elapsedTime": {"millis": 450000000}, "remainingTime": {"millis": -18000000},
            }}),
            issue("TACEA-2", customfield_12152=None, customfield_12151={"ongoingCycle": {
                "breached": True, "paused": False, "goalDuration": {"millis": 576000000},
                "elapsedTime": {"millis": 579600000}, "remainingTime": {"millis": -3600000},
            }}),
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            data = {"issues": candidates, "isLast": True} if request.url.path.endswith("/search/jql") else history_page()
            return httpx.Response(200, json=data)

        first, second = await self.collect(handler)
        self.assertEqual([14400000, 144000000, 432000000], [cycle.goal_ms for cycle in first.cycles])
        self.assertEqual([0, 7200000, 18000000], [cycle.exceeded_ms for cycle in first.cycles])
        self.assertEqual([False, False, True], [cycle.ongoing for cycle in first.cycles])
        self.assertEqual([None, None, True], [cycle.paused for cycle in first.cycles])
        self.assertIsNone(first.cycles[0].breached_at)
        self.assertEqual(_START, first.cycles[0].started_at)
        self.assertEqual(datetime(2026, 10, 10, tzinfo=_KST), first.cycles[0].stopped_at)
        self.assertIsNone(first.cycles[2].stopped_at)
        self.assertEqual((576000000, 3600000), (second.cycles[0].goal_ms, second.cycles[0].exceeded_ms))
        self.assertFalse(second.cycles[0].paused)

    async def test_missing_and_invalid_times_remain_unknown_but_remaining_can_supply_excess(self) -> None:
        cycles = [
            {"breached": True},
            {"breached": True, "remainingTime": {"millis": -90000}},
            {"breached": True, "goalDuration": {"millis": 0}, "elapsedTime": {"millis": 1000}},
            {"breached": True, "goalDuration": {"millis": 10}, "elapsedTime": {"millis": 20}, "remainingTime": {"millis": -9}},
            {"breached": True, "goalDuration": {"millis": 10}, "elapsedTime": {"millis": 9}},
            {"breached": False, "goalDuration": {"millis": 10}, "elapsedTime": {"millis": 11}},
            {"breached": True, "remainingTime": {"millis": 10}},
            *({"breached": True, "goalDuration": {"millis": value}, "elapsedTime": {"millis": value}, "remainingTime": {"millis": value}} for value in (True, "3600", 1.5, None, [], {})),
            {"breached": True, "goalDuration": {"millis": -1}, "elapsedTime": {"millis": -2}},
            {"breached": True, "goalDuration": "invalid", "elapsedTime": []},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            candidate = issue(customfield_12152={"completedCycles": cycles}, customfield_12151={"ongoingCycle": {"breached": False, "paused": "true"}})
            data = {"issues": [candidate], "isLast": True} if request.url.path.endswith("/search/jql") else history_page()
            return httpx.Response(200, json=data)

        result = (await self.collect(handler))[0]
        self.assertEqual([None, 90000, 1000, None, None, None, None], [cycle.exceeded_ms for cycle in result.cycles[:7]])
        self.assertTrue(all(cycle.goal_ms is None and cycle.elapsed_ms is None and cycle.exceeded_ms is None for cycle in result.cycles[7:]))
        self.assertIsNone(result.cycles[-1].paused)
        self.assertTrue(any("일치하지" in warning for warning in result.warnings))
        self.assertTrue(any("유효하지" in warning for warning in result.warnings))

    async def test_resolves_assets_and_preserves_unknown_partner(self) -> None:
        candidates = [
            issue("TACEA-1", customfield_11022=None, customfield_10854=[{"workspaceId": "space", "objectId": "customer"}], customfield_10859=[{"workspaceId": "space", "objectId": "partner"}]),
            issue("TACEA-2", customfield_10859=[{"objectId": "unresolved"}]),
            issue("TACEA-3", customfield_10859=None),
            issue("TACEA-4", customfield_10859=[{"workspaceId": "space", "objectId": "unnamed"}]),
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                return httpx.Response(200, json={"issues": candidates, "isLast": True})
            if "/object/" in request.url.path:
                value = request.url.path.rsplit("/", 1)[1]
                return httpx.Response(200, json={"label": {"customer": "서울교통공사", "partner": "에이치씨인포"}.get(value, "")})
            return httpx.Response(200, json=history_page())

        result = await self.collect(handler)
        self.assertEqual("서울교통공사", result[0].customer)
        self.assertEqual(("에이치씨인포",), result[0].partners)
        self.assertIsNone(result[1].partners)
        self.assertEqual((), result[2].partners)
        self.assertIsNone(result[3].partners)
        self.assertIn("담당 파트너사 확인 불가", result[1].warnings)

    async def test_incomplete_history_keeps_ticket_with_unknown_history(self) -> None:
        cases = (
            {"values": [], "startAt": 0, "total": 2},
            {"values": [], "startAt": 1, "total": 0},
            {"values": [history("1", "invalid", "할 일", "결과 대기 중")], "startAt": 0, "total": 1},
            {"values": [history("1", "2026-10-02T00:00:00Z", "", "결과 대기 중")], "startAt": 0, "total": 1},
        )
        for page in cases:
            with self.subTest(page=page):
                def handler(request: httpx.Request) -> httpx.Response:
                    data = {"issues": [issue()], "isLast": True} if request.url.path.endswith("/search/jql") else page
                    return httpx.Response(200, json=data)

                result = (await self.collect(handler))[0]
                self.assertFalse(result.history_complete)
                self.assertTrue(any("불완전" in warning for warning in result.warnings))

    async def test_repeated_or_changed_history_is_marked_incomplete(self) -> None:
        for changed_total in (False, True):
            with self.subTest(changed_total=changed_total):
                def handler(request: httpx.Request) -> httpx.Response:
                    if request.url.path.endswith("/search/jql"):
                        return httpx.Response(200, json={"issues": [issue()], "isLast": True})
                    start = int(request.url.params["startAt"])
                    total = 3 if start and changed_total else 2
                    return httpx.Response(200, json=history_page([history("same", "2026-10-02T00:00:00Z", "할 일", "결과 대기 중")], start, total))

                self.assertFalse((await self.collect(handler))[0].history_complete)

    async def test_same_status_ids_normalize_localized_and_renamed_history_labels(self) -> None:
        first = history("1", "2026-10-02T00:00:00+09:00", "할 일", "In Review")
        first["items"][0].update({"from": "1", "to": "2"})
        second = history("2", "2026-10-03T00:00:00+09:00", "연구소 검토 중", "Closed")
        second["items"][0].update({"from": "2", "to": "3"})
        candidate = issue(status={"id": "3", "name": "닫힘"}, customfield_12152={"completedCycles": [
            {"breached": True, "breachTime": {"iso8601": "2026-10-02T12:00:00+09:00"}},
        ]})

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                return httpx.Response(200, json={"issues": [candidate], "isLast": True})
            return httpx.Response(200, json=history_page([first, second], total=2))

        issues = await self.collect(handler)
        report = build_sla_violation_report(issues, "month", date(2026, 10, 7), datetime(2026, 10, 14, tzinfo=_KST), "tester")
        self.assertTrue(issues[0].history_complete)
        self.assertEqual("연구소 검토 중", report.tickets[0].breaches[0].status)
        self.assertIsNone(report.tickets[0].status_durations)
        self.assertEqual("resolution_sla", report.tickets[0].status_durations_basis)
        self.assertTrue(report.tickets[0].warnings)

    async def test_missing_or_conflicting_status_ids_do_not_hide_history_gaps(self) -> None:
        for conflicting_ids in (False, True):
            with self.subTest(conflicting_ids=conflicting_ids):
                change = history("1", "2026-10-02T00:00:00+09:00", "할 일", "닫힘" if conflicting_ids else "Closed")
                if conflicting_ids:
                    change["items"][0].update({"from": "1", "to": "different-closed-status"})
                candidate = issue(status={"id": "closed-status", "name": "닫힘"})

                def handler(request: httpx.Request) -> httpx.Response:
                    if request.url.path.endswith("/search/jql"):
                        return httpx.Response(200, json={"issues": [candidate], "isLast": True})
                    return httpx.Response(200, json=history_page([change], total=1))

                issues = await self.collect(handler)
                report = build_sla_violation_report(issues, "month", date(2026, 10, 7), datetime(2026, 10, 14, tzinfo=_KST), "tester")
                self.assertIsNone(report.tickets[0].status_durations)
                self.assertIsNone(report.tickets[0].breaches[0].status)

    async def test_failed_provider_requests_propagate(self) -> None:
        for failure in ("search", "history", "asset"):
            with self.subTest(failure=failure):
                def handler(request: httpx.Request) -> httpx.Response:
                    endpoint = "search" if request.url.path.endswith("/search/jql") else "asset" if "/object/" in request.url.path else "history"
                    if endpoint == failure:
                        return httpx.Response(503)
                    if endpoint == "search":
                        return httpx.Response(200, json={"issues": [issue(customfield_10859=[{"workspaceId": "space", "objectId": "partner"}])], "isLast": True})
                    return httpx.Response(200, json=history_page())

                with self.assertRaisesRegex(RuntimeError, "Jira SLA violation request failed") as raised:
                    await self.collect(handler)
                self.assertIsInstance(raised.exception.__cause__, httpx.HTTPStatusError)

    async def test_transport_and_json_errors_use_application_error_contract(self) -> None:
        for invalid_json in (False, True):
            with self.subTest(invalid_json=invalid_json):
                def handler(request: httpx.Request) -> httpx.Response:
                    if invalid_json:
                        return httpx.Response(200, content=b"not JSON")
                    raise httpx.ReadTimeout("timeout", request=request)

                with self.assertRaisesRegex(RuntimeError, "Jira SLA violation request failed"):
                    await self.collect(handler)

    async def test_repeated_or_truncated_search_fails_instead_of_saving_partial_data(self) -> None:
        for repeated in (False, True):
            with self.subTest(repeated=repeated):
                calls = 0

                def handler(request: httpx.Request) -> httpx.Response:
                    nonlocal calls
                    calls += 1
                    data = {"issues": [issue(f"TACEA-{calls}")], "isLast": False}
                    if repeated:
                        data["nextPageToken"] = "same"
                    return httpx.Response(200, json=data)

                with self.assertRaisesRegex(RuntimeError, "truncated|repeated"):
                    await self.collect(handler)

    async def test_invalid_sla_data_fails_instead_of_hiding_violations(self) -> None:
        for value in ("invalid", {"completedCycles": "invalid"}, {"ongoingCycle": {"breached": "true"}}):
            with self.subTest(value=value):
                def handler(request: httpx.Request) -> httpx.Response:
                    return httpx.Response(200, json={"issues": [issue(customfield_12152=value)], "isLast": True})

                with self.assertRaisesRegex(RuntimeError, "SLA.*invalid"):
                    await self.collect(handler)

    async def test_requests_configured_fields_and_always_refreshes(self) -> None:
        searches = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                searches.append(json.loads(request.content))
                return httpx.Response(200, json={"issues": [issue(customfield_90001={"ongoingCycle": {"breached": True}}, customfield_90002=None, customfield_90003={"displayName": "지정 담당자"})], "isLast": True})
            return httpx.Response(200, json=history_page())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = SlaViolationJiraSource("https://jira.example.com", "user", "token", sla_initial_response_field_id="customfield_90001", sla_resolution_field_id="customfield_90002", tac_assignee_field_id="customfield_90003", client=client)
            first = await source.fetch_issues(_START, _END)
            await source.fetch_issues(_START, _END)
            await source.aclose()
            await source.aclose()
            self.assertFalse(client.is_closed)
            with self.assertRaisesRegex(RuntimeError, "closed"):
                await source.fetch_issues(_START, _END)
        self.assertEqual(2, len(searches))
        self.assertEqual("지정 담당자", first[0].tac_assignee)
        self.assertTrue({"customfield_90001", "customfield_90002", "customfield_90003"}.issubset(searches[0]["fields"]))

    async def test_close_cancels_pending_work(self) -> None:
        started = asyncio.Event()
        canceled = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                canceled.set()
                raise

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client)
            pending = asyncio.create_task(source.fetch_issues(_START, _END))
            await started.wait()
            await source.aclose()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertTrue(canceled.is_set())

    async def test_limits_concurrent_issue_requests_to_five(self) -> None:
        active = 0
        maximum = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal active, maximum
            if request.url.path.endswith("/search/jql"):
                return httpx.Response(200, json={"issues": [issue(f"TACEA-{index}") for index in range(12)], "isLast": True})
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.001)
            active -= 1
            return httpx.Response(200, json=history_page())

        self.assertEqual(12, len(await self.collect(handler)))
        self.assertEqual(5, maximum)

    async def test_validates_configuration_and_period(self) -> None:
        for kwargs in ({"project_key": 'TACEA" OR'}, {"sla_initial_response_field_id": ""}, {"sla_resolution_field_id": "customfield_12152"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SlaViolationJiraSource("https://jira.example.com", "user", "token", **kwargs)
        async with SlaViolationJiraSource("https://jira.example.com", "user", "token") as source:
            with self.assertRaises(ValueError):
                await source.fetch_issues(datetime(2026, 10, 1), _END)
            with self.assertRaises(ValueError):
                await source.fetch_issues(_END, _START)
        self.assertTrue(source._client.is_closed)
