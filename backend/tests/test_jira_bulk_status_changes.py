# backend/tests/test_jira_bulk_status_changes.py
import json
import unittest
from copy import deepcopy

import httpx

from src.application.ports.jira_port import JiraIssue
from src.infrastructure.external.jira_client import JiraClient


def history(identifier="1", created=1793152252051, target="6", name="Closed"):
    return {"id": identifier, "created": created, "items": [{
        "fieldId": "status", "from": "10672", "fromString": "결과 대기 중",
        "to": target, "toString": name,
    }]}


def page(histories, identifier="32968", token=None):
    result = {"issueChangeLogs": [{"issueId": identifier, "changeHistories": histories}]}
    if token is not None:
        result["nextPageToken"] = token
    return result


class JiraBulkStatusChangesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = JiraClient("https://jira.example.com", "user", "token")
        await self.jira._client.aclose()
        self.requests = []
        self.responses = [page([history()])]

        def handler(request):
            self.requests.append(request)
            response = self.responses.pop(0)
            return response if isinstance(response, httpx.Response) else httpx.Response(200, json=response)

        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.issues = [JiraIssue(key="TACEA-3340", issue_id="32968")]

    async def asyncTearDown(self):
        await self.jira.aclose()

    async def test_paginates_all_histories_and_preserves_ids_with_utc_timestamps(self):
        self.responses = [page([history()], token="next"), page([
            history("2", "2026-04-23T15:03:03.730+0900"),
            history("3", "2026-05-28T08:25:45.140+0900", "10678", "재 오픈"),
        ])]
        result = await self.jira.get_issue_status_changes_batch(self.issues)
        self.assertEqual(3, len(result["TACEA-3340"]))
        self.assertEqual("2026-10-28T01:50:52.051000+00:00", result["TACEA-3340"][0].changed_at)
        self.assertEqual("2026-04-23T06:03:03.730000+00:00", result["TACEA-3340"][1].changed_at)
        self.assertEqual("6", result["TACEA-3340"][0].to_status_id)
        self.assertEqual("10672", result["TACEA-3340"][0].from_status_id)
        self.assertEqual("Closed", result["TACEA-3340"][0].to_status)
        bodies = [json.loads(request.content) for request in self.requests]
        self.assertEqual({"issueIdsOrKeys": ["32968"], "fieldIds": ["status"], "maxResults": 1000}, bodies[0])
        self.assertEqual("next", bodies[1]["nextPageToken"])
        self.assertTrue(all(request.url.path == "/rest/api/3/changelog/bulkfetch" for request in self.requests))

    async def test_splits_large_input_and_returns_explicit_empty_histories(self):
        issues = [JiraIssue(key=f"TACEA-{index}", issue_id=str(index)) for index in range(1001)]
        self.responses = [{"issueChangeLogs": []}, {"issueChangeLogs": []}]
        result = await self.jira.get_issue_status_changes_batch(issues)
        self.assertEqual({issue.key: [] for issue in issues}, result)
        self.assertEqual([1000, 1], [len(json.loads(request.content)["issueIdsOrKeys"]) for request in self.requests])
        self.assertEqual({}, await self.jira.get_issue_status_changes_batch([]))
        self.assertEqual(2, len(self.requests))

    async def test_duplicate_input_is_deduplicated_but_ambiguous_identity_fails(self):
        result = await self.jira.get_issue_status_changes_batch(self.issues * 2)
        self.assertEqual(["TACEA-3340"], list(result))
        self.assertEqual(["32968"], json.loads(self.requests[0].content)["issueIdsOrKeys"])
        for extra in (JiraIssue(key="TACEA-3340", issue_id="2"), JiraIssue(key="TACEA-2", issue_id="32968"), JiraIssue(key="TACEA-3")):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                await self.jira.get_issue_status_changes_batch([*self.issues, extra])
        self.assertEqual(1, len(self.requests))

    async def test_repeated_tokens_and_empty_advancing_pages_fail(self):
        for responses in (
            [page([history()], token="same"), page([history("2")], token="same")],
            [{"issueChangeLogs": [], "nextPageToken": "next"}],
            [page([history()], token="first"), page([history()], token="second")],
        ):
            self.responses = responses
            with self.subTest(responses=responses), self.assertRaisesRegex(RuntimeError, "did not advance"):
                await self.jira.get_issue_status_changes_batch(self.issues)

    async def test_duplicate_boundary_history_is_not_returned_twice(self):
        self.responses = [page([history()], token="next"), page([history(), history("2")])]
        result = await self.jira.get_issue_status_changes_batch(self.issues)
        self.assertEqual(2, len(result["TACEA-3340"]))

    async def test_inconsistent_duplicate_history_fails(self):
        self.responses = [page([history()], token="next"), page([history(created=1793152252052)])]
        with self.assertRaisesRegex(RuntimeError, "changed during pagination"):
            await self.jira.get_issue_status_changes_batch(self.issues)

    async def test_malformed_payloads_are_not_treated_as_empty_history(self):
        invalid = [[], {}, {"issueChangeLogs": {}}, page([], "unknown"),
                   {"issueChangeLogs": [{"issueId": {}, "changeHistories": []}]},
                   page([{"id": "1", "items": [], "created": "invalid"}]),
                   page([history(created=True)]), page([history(created="2026-10-28")]),
                   page([history(created=10 ** 30)]), page([history(target={})]),
                   page([history(target="", name="")]), page([history()], token=[]),
                   page([{"created": 1793152252051, "items": []}]), page([{"id": "1", "created": 1793152252051, "items": [None]}])]
        for data in invalid:
            self.responses = [deepcopy(data)]
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                await self.jira.get_issue_status_changes_batch(self.issues)

    async def test_http_failure_is_propagated_without_partial_result(self):
        self.responses = [page([history()], token="next"), httpx.Response(429)]
        with self.assertRaisesRegex(RuntimeError, "query failed"):
            await self.jira.get_issue_status_changes_batch(self.issues)

    async def test_project_status_names_use_ids_and_deduplicate_across_issue_types(self):
        self.responses = [[{"statuses": [{"id": "6", "name": "닫힘"}, {"id": "1", "name": "열림"}]}, {"statuses": [{"id": "6", "name": "닫힘"}]}]]
        self.assertEqual({"6": "닫힘", "1": "열림"}, await self.jira.get_project_status_names("TACEA"))
        self.assertEqual("/rest/api/3/project/TACEA/statuses", self.requests[0].url.path)
        self.assertEqual("GET", self.requests[0].method)

    async def test_project_status_invalid_or_conflicting_names_fail(self):
        for data in ({}, [{}], [{"statuses": {}}], [{"statuses": [{"id": "6", "name": ""}]}],
                     [{"statuses": [{"id": "6", "name": "닫힘"}, {"id": "6", "name": "Closed"}]}]):
            self.responses = [data]
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                await self.jira.get_project_status_names("TACEA")

    async def test_issue_mapping_preserves_identity_without_affecting_display_status(self):
        issue = self.jira._map_issue({"id": "32968", "key": "TACEA-3340", "fields": {"status": {"id": "6", "name": "닫힘"}}})
        self.assertEqual(("32968", "6", "닫힘"), (issue.issue_id, issue.status_id, issue.status))


if __name__ == "__main__":
    unittest.main()
