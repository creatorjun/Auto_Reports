# backend/tests/test_jira_client_description.py
import unittest
from unittest.mock import patch

import httpx

from src.infrastructure.external.jira_client import JiraClient


def paragraph(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


class JiraClientDescriptionTest(unittest.IsolatedAsyncioTestCase):
    async def client(self, handler):
        client = JiraClient("https://jira.example.com", "test-user", "test-token")
        await client._client.aclose()
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return client

    async def test_requests_description_and_rendered_images_without_returning_html(self):
        requests = []
        payload = {
            "fields": {"description": {"type": "doc", "content": [paragraph("본문 첫 문단"), paragraph("두 번째 문단")]}},
            "renderedFields": {"description": '<p>실행하지 않는 HTML</p><script>alert(1)</script><img src="/rest/api/3/attachment/content/10017" alt="캡처 &amp; 로그"><img src="/secure/attachment/10017/same.png"><img src="/secure/attachment/10018/other.png"><img src="https://untrusted.example/image.png">'},
        }

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=payload)

        client = await self.client(handler)
        description = await client.get_issue_description("TACEA-4501")
        self.assertEqual("/rest/api/3/issue/TACEA-4501", requests[0].url.path)
        self.assertEqual({"fields": "description", "expand": "renderedFields"}, dict(requests[0].url.params))
        self.assertEqual("본문 첫 문단\n두 번째 문단", description.body)
        self.assertNotIn("alert", description.body)
        self.assertNotIn("HTML", description.body)
        self.assertEqual([("10017", "캡처 & 로그"), ("10018", "본문 첨부 이미지")], [(image.attachment_id, image.alt) for image in description.images])

    async def test_plain_text_preserves_nested_lists_numbering_table_rows_and_code(self):
        description = {"type": "doc", "content": [
            paragraph("개요"),
            {"type": "bulletList", "content": [{"type": "listItem", "content": [paragraph("점검"), {"type": "bulletList", "content": [{"type": "listItem", "content": [paragraph("하위")]}]}]}]},
            {"type": "orderedList", "attrs": {"order": 3}, "content": [{"type": "listItem", "content": [paragraph("재현")]}, {"type": "listItem", "content": [paragraph("확인")]}]},
            {"type": "table", "content": [
                {"type": "tableRow", "content": [{"type": "tableHeader", "content": [paragraph("항목")]}, {"type": "tableHeader", "content": [paragraph("결과")]}]},
                {"type": "tableRow", "content": [{"type": "tableCell", "content": [paragraph("서버")]}, {"type": "tableCell", "content": [paragraph("정상")]}]},
            ]},
            {"type": "codeBlock", "content": [{"type": "text", "text": "if ready:\n    run()"}]},
        ]}
        client = await self.client(lambda request: httpx.Response(200, json={"fields": {"description": description}}))
        result = await client.get_issue_description("TACEA-4501")
        self.assertEqual("개요\n- 점검\n  - 하위\n3. 재현\n4. 확인\n항목 | 결과\n서버 | 정상\nif ready:\n    run()", result.body)
        self.assertEqual((), result.images)

    async def test_empty_description_and_plain_string_are_valid_and_never_cached(self):
        descriptions = [None, "새 본문", {"type": "doc", "content": []}]
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"fields": {"description": descriptions[len(requests) - 1]}, "renderedFields": None})

        client = await self.client(handler)
        results = [await client.get_issue_description("TACEA-4501") for _ in descriptions]
        self.assertEqual(["", "새 본문", ""], [result.body for result in results])
        self.assertTrue(all(result.images == () for result in results))
        self.assertEqual(3, len(requests))

    async def test_missing_issue_differs_from_empty_description_and_upstream_errors(self):
        responses = [httpx.Response(404), httpx.Response(403), httpx.Response(503), httpx.Response(200, content=b"not JSON")]
        client = await self.client(lambda request: responses.pop(0))
        self.assertIsNone(await client.get_issue_description("TACEA-4501"))
        for _ in range(3):
            with self.assertRaisesRegex(RuntimeError, "Jira description request failed"):
                await client.get_issue_description("TACEA-4501")

    async def test_malformed_payload_never_becomes_an_empty_description(self):
        payloads = [None, [], {}, {"fields": None}, {"fields": {}}, {"fields": {"description": []}}, {"fields": {"description": False}}, {"fields": {"description": None}, "renderedFields": []}, {"fields": {"description": None}, "renderedFields": {"description": {}}}]
        client = await self.client(lambda request: httpx.Response(200, json=payloads.pop(0)))
        for _ in range(len(payloads)):
            with self.assertRaisesRegex(RuntimeError, "Jira description request failed"):
                await client.get_issue_description("TACEA-4501")

    async def test_description_image_reuses_safe_attachment_type_and_size_limits(self):
        responses = [
            httpx.Response(200, content=b"png", headers={"Content-Type": "image/png"}),
            httpx.Response(200, content=b"<svg/>", headers={"Content-Type": "image/svg+xml"}),
            httpx.Response(200, content=b"large", headers={"Content-Type": "image/png"}),
        ]
        requests = []

        def handler(request):
            requests.append(request)
            return responses.pop(0)

        client = await self.client(handler)
        with patch("src.infrastructure.external.jira_client._COMMENT_IMAGE_MAX_BYTES", 4):
            self.assertEqual(b"png", (await client.get_attachment_content("10017")).data)
            with self.assertRaisesRegex(RuntimeError, "Unsupported"):
                await client.get_attachment_content("10017")
            with self.assertRaisesRegex(RuntimeError, "too large"):
                await client.get_attachment_content("10017")
        self.assertTrue(all(request.url.host == "jira.example.com" for request in requests))
        self.assertTrue(all(request.url.params["redirect"] == "false" for request in requests))
