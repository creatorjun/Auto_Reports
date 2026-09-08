# backend/tests/test_jira_client_issue_types.py
import asyncio
import json
import unittest

import httpx

from src.infrastructure.external.jira_client import JiraClient


class JiraClientIssueTypesTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_identical_queries_share_inflight_requests(self) -> None:
        requests = {"issues": 0, "counts": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/search/jql"):
                requests["issues"] += 1
                await asyncio.sleep(0.01)
                return httpx.Response(200, json={"issues": [{"key": "TACEA-1"}]})
            requests["counts"] += 1
            await asyncio.sleep(0.01)
            return httpx.Response(200, json={"count": 7})

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            issue_results = await asyncio.gather(*(
                client.get_issues("project = TACEA", fields="summary")
                for _ in range(20)
            ))
            count_results = await asyncio.gather(*(
                client.get_issue_count("project = TACEA")
                for _ in range(20)
            ))
        finally:
            await client.aclose()

        self.assertTrue(all(result == [{"key": "TACEA-1"}] for result in issue_results))
        self.assertEqual([7] * 20, count_results)
        self.assertEqual({"issues": 1, "counts": 1}, requests)

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

    async def test_comment_pages_use_offsets_and_fetch_each_request(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            offset = int(request.url.params["startAt"])
            limit = int(request.url.params["maxResults"])
            return httpx.Response(200, json={
                "comments": [
                    {"id": str(12 - index)}
                    for index in range(offset, min(offset + limit, 12))
                ],
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            first = await client.get_issue_comments("TACEA-4501", max_results=6)
            second = await client.get_issue_comments("TACEA-4501", max_results=6, offset=5)
            first_reloaded = await client.get_issue_comments("TACEA-4501", max_results=6)
            second_reloaded = await client.get_issue_comments(
                "TACEA-4501", max_results=6, offset=5,
            )
            smaller = await client.get_issue_comments("TACEA-4501", max_results=5)
        finally:
            await client.aclose()

        self.assertEqual(["12", "11", "10", "9", "8", "7"], [c["id"] for c in first])
        self.assertEqual(["7", "6", "5", "4", "3", "2"], [c["id"] for c in second])
        self.assertEqual(first, first_reloaded)
        self.assertEqual(second, second_reloaded)
        self.assertEqual(first[:5], smaller)
        self.assertEqual(5, len(requests))
        self.assertEqual(["0", "5", "0", "5", "0"], [r.url.params["startAt"] for r in requests])
        self.assertTrue(all(r.url.params["orderBy"] == "-created" for r in requests))
        self.assertTrue(all(r.url.params["expand"] == "renderedBody" for r in requests))

    async def test_identical_comment_request_refetches_inserted_and_deleted_comments(self) -> None:
        comments = [{"id": str(index)} for index in range(20, 0, -1)]
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            offset = int(request.url.params["startAt"])
            limit = int(request.url.params["maxResults"])
            return httpx.Response(200, json={
                "total": len(comments),
                "comments": comments[offset:offset + limit],
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            first = await client.get_issue_comments("TACEA-4501", max_results=11)
            comments.insert(0, {"id": "21"})
            second = await client.get_issue_comments("TACEA-4501", max_results=11)
            comments.remove({"id": "20"})
            third = await client.get_issue_comments("TACEA-4501", max_results=11)
        finally:
            await client.aclose()

        self.assertEqual([str(index) for index in range(20, 9, -1)], [c["id"] for c in first])
        self.assertEqual([str(index) for index in range(21, 10, -1)], [c["id"] for c in second])
        self.assertEqual(["21", *[str(index) for index in range(19, 9, -1)]], [c["id"] for c in third])
        self.assertEqual(3, len(requests))

    async def test_loads_single_comment_scoped_to_issue_with_rendered_body(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/99999"):
                return httpx.Response(404)
            if request.url.path.endswith("/10002"):
                return httpx.Response(503)
            return httpx.Response(200, json={
                "id": "10001",
                "renderedBody": '<img src="/secure/attachment/10017/capture.png">',
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            comment = await client.get_issue_comment("TACEA-4501", "10001")
            missing = await client.get_issue_comment("TACEA-4501", "99999")
            with self.assertRaises(RuntimeError):
                await client.get_issue_comment("TACEA-4501", "10002")
        finally:
            await client.aclose()

        self.assertEqual("10001", comment["id"])
        self.assertIn("10017", comment["renderedBody"])
        self.assertIsNone(missing)
        self.assertEqual(
            "/rest/api/3/issue/TACEA-4501/comment/10001", requests[0].url.path,
        )
        self.assertTrue(all(r.url.params["expand"] == "renderedBody" for r in requests))

    async def test_large_comment_limit_reads_only_requested_rows_and_stops_at_total(self) -> None:
        requests: list[tuple[int, int]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            offset = int(request.url.params["startAt"])
            limit = int(request.url.params["maxResults"])
            requests.append((offset, limit))
            return httpx.Response(200, json={
                "total": 130,
                "comments": [
                    {"id": str(index)}
                    for index in range(offset, min(offset + limit, 130))
                ],
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            comments = await client.get_issue_comments("TACEA-4501", max_results=106)
            final = await client.get_issue_comments("TACEA-4501", max_results=16, offset=125)
        finally:
            await client.aclose()

        self.assertEqual([str(index) for index in range(106)], [c["id"] for c in comments])
        self.assertEqual([str(index) for index in range(125, 130)], [c["id"] for c in final])
        self.assertEqual([(0, 100), (100, 6), (125, 16)], requests)

    async def test_comment_limit_handles_smaller_jira_pages_until_requested_size(self) -> None:
        requests: list[tuple[int, int]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            offset = int(request.url.params["startAt"])
            limit = int(request.url.params["maxResults"])
            requests.append((offset, limit))
            return httpx.Response(200, json={
                "total": 12,
                "comments": [
                    {"id": str(index)}
                    for index in range(offset, min(offset + limit, offset + 4, 12))
                ],
            })

        client = JiraClient("https://jira.example.com", "user", "token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            comments = await client.get_issue_comments("TACEA-4501", max_results=11)
        finally:
            await client.aclose()

        self.assertEqual([str(index) for index in range(11)], [c["id"] for c in comments])
        self.assertEqual([(0, 11), (4, 7), (8, 3)], requests)
