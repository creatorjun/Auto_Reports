# backend/tests/test_jira_client_issue_types.py
import unittest

import httpx

from src.infrastructure.external.jira_client import JiraClient


class JiraClientIssueTypesTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_unique_non_subtask_project_issue_types(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("/rest/api/3/project/TACEA", request.url.path)
            self.assertEqual("issueTypes", request.url.params["expand"])
            return httpx.Response(200, json={
                "issueTypes": [
                    {"name": "인시던트", "subtask": False},
                    {"name": "H/W 장애 요청", "subtask": False},
                    {"name": "하위 작업", "subtask": True},
                    {"name": "인시던트", "subtask": False},
                    {"name": "", "subtask": False},
                ],
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.get_project_issue_types("TACEA")
        finally:
            await client.aclose()

        self.assertEqual(["인시던트", "H/W 장애 요청"], result)
