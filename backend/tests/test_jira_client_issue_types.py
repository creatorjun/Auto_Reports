# backend/tests/test_jira_client_issue_types.py
import json
import unittest

import httpx

from src.infrastructure.external.jira_client import JiraClient


class JiraClientIssueTypesTest(unittest.IsolatedAsyncioTestCase):
    async def test_unlimited_issue_search_reads_every_page(self) -> None:
        requests: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            requests.append(payload)
            if "nextPageToken" not in payload:
                return httpx.Response(
                    200,
                    json={
                        "issues": [{"key": f"TACEA-{index}"} for index in range(1, 101)],
                        "nextPageToken": "page-2",
                    },
                )
            return httpx.Response(200, json={"issues": [{"key": "TACEA-101"}]})

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.get_issues(
                "project = TACEA",
                max_results=None,
                fields="summary",
            )
        finally:
            await client.aclose()

        self.assertEqual(101, len(result))
        self.assertEqual(2, len(requests))
        self.assertEqual("page-2", requests[1]["nextPageToken"])

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

    async def test_requests_rendered_comments_and_downloads_supported_image(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/comment"):
                return httpx.Response(200, json={"comments": [{"id": "10001"}]})
            if request.headers["Accept"] == "image/*":
                return httpx.Response(406)
            return httpx.Response(
                200,
                content=b"png-data",
                headers={"Content-Type": "image/png"},
            )

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            comments = await client.get_issue_comments("TACEA-4501")
            image = await client.get_attachment_content("10017")
        finally:
            await client.aclose()

        self.assertEqual([{"id": "10001"}], comments)
        self.assertEqual("renderedBody", requests[0].url.params["expand"])
        self.assertEqual(
            "/rest/api/3/attachment/content/10017",
            requests[1].url.path,
        )
        self.assertEqual("false", requests[1].url.params["redirect"])
        self.assertEqual("*/*", requests[1].headers["Accept"])
        self.assertEqual(b"png-data", image.data)
        self.assertEqual("image/png", image.media_type)
