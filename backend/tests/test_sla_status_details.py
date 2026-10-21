# backend/tests/test_sla_status_details.py
import json
import unittest

import httpx

from src.infrastructure.external.sla_violation_jira_source import SlaViolationJiraSource
from tests.test_sla_violation_jira_source import history_page, issue


class SlaStatusDetailsTest(unittest.IsolatedAsyncioTestCase):
    async def test_unbreached_candidates_keep_metadata_and_verified_history(self):
        requests = []
        candidate = issue(
            status={"name": "구현 중", "statusCategory": {"key": "indeterminate"}},
            issuetype={"name": "개선"},
            customfield_12152={"completedCycles": []},
            customfield_12151={"ongoingCycle": {
                "breached": False, "paused": False,
                "goalDuration": {"millis": 10000}, "elapsedTime": {"millis": 8000},
                "remainingTime": {"millis": 2000},
                "startTime": {"iso8601": "2026-10-01T00:00:00+09:00"},
            }},
        )

        def handler(request):
            requests.append(request)
            payload = {"issues": [candidate], "isLast": True} if request.method == "POST" else history_page()
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                result = await source.fetch_details(("TACEA-1", "TACEA-1"))
        self.assertEqual(1, len(result))
        self.assertEqual("구현 중", result[0].current_status)
        self.assertEqual("개선", result[0].issue_type)
        self.assertEqual("서울교통공사", result[0].customer)
        self.assertTrue(result[0].history_complete)
        self.assertEqual(8000, result[0].cycles[0].elapsed_ms)
        self.assertFalse(result[0].cycles[0].breached)
        self.assertIsNotNone(result[0].clock_snapshot_after)
        payload = json.loads(requests[0].content)
        self.assertIn('project = "TACEA"', payload["jql"])
        self.assertIn('key IN ("TACEA-1")', payload["jql"])
        self.assertIn('statusCategory != Done', payload["jql"])
        self.assertNotIn('created >=', payload["jql"])
        self.assertEqual(2, len(requests))

    async def test_empty_or_invalid_keys_do_not_query_jira(self):
        requests = []
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: requests.append(request))) as client:
            async with SlaViolationJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                self.assertEqual((), await source.fetch_details(()))
                for key in ('TACEA-1" OR key IS NOT EMPTY', '../TACEA-1', ''):
                    with self.assertRaises(ValueError):
                        await source.fetch_details((key,))
        self.assertEqual([], requests)

    async def test_null_completed_cycles_keep_unbreached_ongoing_status_details(self):
        candidate = issue(
            customfield_12152={"completedCycles": None},
            customfield_12151={"completedCycles": None, "ongoingCycle": {
                "breached": False, "paused": True,
                "goalDuration": {"millis": 100_000}, "elapsedTime": {"millis": 80_000},
                "remainingTime": {"millis": 20_000},
            }},
        )

        def handler(request):
            payload = {"issues": [candidate], "isLast": True} if request.method == "POST" else history_page()
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                result = await source.fetch_details(("TACEA-1",))
        self.assertEqual(1, len(result))
        self.assertEqual(1, len(result[0].cycles))
        cycle = result[0].cycles[0]
        self.assertEqual(("resolution", True, True, False, 100_000, 80_000), (
            cycle.metric, cycle.ongoing, cycle.paused, cycle.breached, cycle.goal_ms, cycle.elapsed_ms,
        ))

    async def test_unrequested_results_fail_instead_of_returning_other_tickets(self):
        def handler(request):
            return httpx.Response(200, json={"issues": [issue("TACEA-2")], "isLast": True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                with self.assertRaisesRegex(RuntimeError, "unrequested"):
                    await source.fetch_details(("TACEA-1",))

    async def test_closed_or_missing_candidates_do_not_load_history(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"issues": [issue(status={"name": "Closed", "statusCategory": {"key": "done"}})], "isLast": True})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            async with SlaViolationJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                self.assertEqual((), await source.fetch_details(("TACEA-1", "TACEA-2")))
        self.assertEqual(1, len(requests))
