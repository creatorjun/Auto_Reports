# backend/tests/test_jira_search.py
import json
import unittest

import httpx

from src.domain.entities.search import SearchSource
from src.infrastructure.external.jira_client import JiraClient


class JiraSearchTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = JiraClient("https://jira.example.test", "user", "token")
        await self.client._client.aclose()
        self.requests = []
        self.failed_source = None

        def handler(request: httpx.Request) -> httpx.Response:
            is_jira = request.method == "POST"
            source = SearchSource.JIRA if is_jira else SearchSource.CONFLUENCE
            self.requests.append((source, request))
            if source == self.failed_source:
                return httpx.Response(503)
            if is_jira:
                return httpx.Response(200, json={"issues": [
                    {"key": f"T-{index}", "fields": {"summary": f"Issue {index}"}}
                    for index in range(8)
                ]})
            return httpx.Response(200, json={"results": [
                {"id": str(index), "title": f"Page {index}", "space": {"key": "DOC"}}
                for index in range(8)
            ]})

        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_default_limit_returns_five_results_per_service(self) -> None:
        results = await self.client.search("search")
        self.assertEqual(10, len(results))
        jira = [result for result in results if result.source == SearchSource.JIRA]
        confluence = [result for result in results if result.source == SearchSource.CONFLUENCE]
        self.assertEqual([f"T-{index}" for index in range(5)], [result.key for result in jira])
        self.assertEqual([str(index) for index in range(5)], [result.key for result in confluence])
        for source, request in self.requests:
            if source == SearchSource.JIRA:
                payload = json.loads(request.content)
                self.assertEqual(5, payload["maxResults"])
                self.assertIn("ORDER BY updated DESC", payload["jql"])
            else:
                self.assertEqual("5", request.url.params["limit"])
                self.assertIn("ORDER BY lastmodified DESC", request.url.params["cql"])

    async def test_custom_limit_is_applied_independently(self) -> None:
        results = await self.client.search("search", limit=2)
        self.assertEqual(4, len(results))
        self.assertEqual(2, sum(result.source == SearchSource.JIRA for result in results))
        self.assertEqual(2, sum(result.source == SearchSource.CONFLUENCE for result in results))

    async def test_failed_service_does_not_remove_other_service_results(self) -> None:
        for failed_source in SearchSource:
            with self.subTest(failed_source=failed_source):
                self.failed_source = failed_source
                results = await self.client.search("search")
                self.assertEqual(5, len(results))
                self.assertTrue(all(result.source != failed_source for result in results))
