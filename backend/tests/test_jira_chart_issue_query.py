# backend/tests/test_jira_chart_issue_query.py
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx
from src.application.ports.jira_port import JiraAssetReference, JiraIssue, JiraIssueField
from src.infrastructure.external.jira_client import JiraClient


class JiraChartIssueQueryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = JiraClient("https://jira.example.test", "test", "test", "customfield_1", "customfield_2")
        await self.jira._client.aclose()

    async def asyncTearDown(self):
        await self.jira.aclose()

    def mock(self, handler):
        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_fresh_query_bypasses_cache_and_identifies_cap(self):
        requests = []
        def handler(request):
            payload = json.loads(request.content)
            requests.append(payload)
            start = int(payload.get("nextPageToken", "0"))
            size = payload["maxResults"]
            issues = [{"key": f"T-{index}", "fields": {"customfield_1": {"completedCycles": [{"breached": True}]}}} for index in range(start, start + size)]
            return httpx.Response(200, json={"issues": issues, "nextPageToken": str(start + size)})
        self.mock(handler)
        fields = frozenset({JiraIssueField.SUMMARY, JiraIssueField.ISSUE_TYPE})
        page = await self.jira.get_report_chart_issues("project = T", 500, fields, with_sla=True)
        self.assertEqual(500, len(page.issues))
        self.assertTrue(page.has_more)
        self.assertEqual(5, len(requests))
        self.assertIn("customfield_1", requests[0]["fields"])
        self.assertIsInstance(page.issues[0], JiraIssue)
        self.assertTrue(page.issues[0].initial_response_breached)
        await self.jira.get_report_chart_issues("project = T", 500, fields, with_sla=True)
        self.assertEqual(10, len(requests))

    async def test_unlimited_query_collects_every_page(self):
        def handler(request):
            payload = json.loads(request.content)
            if "nextPageToken" not in payload:
                return httpx.Response(200, json={"issues": [{"key": "T-1"}], "nextPageToken": "second"})
            return httpx.Response(200, json={"issues": [{"key": "T-2"}]})
        self.mock(handler)
        page = await self.jira.get_report_chart_issues("project = T", None, frozenset({JiraIssueField.SUMMARY}))
        self.assertEqual(["T-1", "T-2"], [issue.key for issue in page.issues])
        self.assertFalse(page.has_more)

    async def test_http_errors_are_not_returned_as_empty_issues(self):
        self.mock(lambda request: httpx.Response(503, text="upstream unavailable"))
        with self.assertRaisesRegex(RuntimeError, "query failed"):
            await self.jira.get_report_chart_issues("project = T", 500, frozenset({JiraIssueField.SUMMARY}))

    async def test_repeated_pagination_token_fails_instead_of_returning_partial_results(self):
        self.mock(lambda request: httpx.Response(200, json={"issues": [{"key": "T-1"}], "nextPageToken": "same"}))
        with self.assertRaisesRegex(RuntimeError, "did not advance"):
            await self.jira.get_report_chart_issues("project = T", None, frozenset({JiraIssueField.SUMMARY}))

    async def test_partner_labels_bypass_cache_and_use_current_assets_response(self):
        reference = JiraAssetReference("workspace", "1")
        self.jira._asset_object_label_cache[reference] = "파트너 객체 1"
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"label": "현재 파트너"})
        self.mock(handler)
        for _ in range(2):
            labels = await self.jira.get_report_chart_asset_labels([reference, reference])
            self.assertEqual("현재 파트너", labels[reference])
        self.assertEqual(2, len(requests))

    async def test_partner_label_failure_is_not_replaced_with_fallback(self):
        self.mock(lambda request: httpx.Response(503, text="unavailable"))
        with self.assertRaisesRegex(RuntimeError, "partner label query failed"):
            await self.jira.get_report_chart_asset_labels([JiraAssetReference("workspace", "1")])

    async def test_partner_label_missing_from_response_fails(self):
        self.mock(lambda request: httpx.Response(200, json={"label": ""}))
        with self.assertRaisesRegex(RuntimeError, "partner label response is invalid"):
            await self.jira.get_report_chart_asset_labels([JiraAssetReference("workspace", "1")])

    async def test_redeployment_fields_are_mapped_at_the_provider_boundary(self):
        requests = []
        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"issues": [{"key": "T-1", "fields": {
                "summary": "재배포", "issuetype": {"name": "개선"},
                "status": {"name": "Closed"}, "resolutiondate": "2024-02-03T09:00:00+0900",
                "customfield_12421": {"value": "2024-02"},
                "customfield_11885": {"value": "수정"},
                "customfield_10859": [{"workspaceId": "workspace", "objectId": "1"}],
            }}]})
        self.mock(handler)
        fields = frozenset({JiraIssueField.SUMMARY, JiraIssueField.ISSUE_TYPE, JiraIssueField.RESOLVED})
        page = await self.jira.get_report_chart_issues("project = T", None, fields, with_redeployment=True)
        self.assertTrue({"customfield_12421", "customfield_11885", "customfield_10859"}.issubset(requests[0]["fields"]))
        self.assertIn("resolutiondate", requests[0]["fields"])
        self.assertEqual(("2024-02", "수정"), (page.issues[0].redeployment_month, page.issues[0].redeployment_cause))
        self.assertEqual((JiraAssetReference("workspace", "1"),), page.issues[0].partner_references)

    async def test_invalid_issue_payload_fails_instead_of_returning_partial_results(self):
        for issues in ([None], [{"fields": []}], [{"fields": {"issuetype": "invalid"}}]):
            with self.subTest(issues=issues):
                self.mock(lambda request: httpx.Response(200, json={"issues": issues}))
                try:
                    with self.assertRaisesRegex(RuntimeError, "response is invalid"):
                        await self.jira.get_report_chart_issues("project = T", 500, frozenset())
                finally:
                    await self.jira._client.aclose()
