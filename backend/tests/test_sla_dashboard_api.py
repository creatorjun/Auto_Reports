# backend/tests/test_sla_dashboard_api.py
import unittest
from unittest.mock import AsyncMock, call

import httpx
from fastapi import FastAPI

from src.application.ports.jira_port import JiraAttachmentContent
from src.domain.entities.sla_dashboard import SlaDashboardCommentPage
from src.presentation.api.v1.deps import get_sla_dashboard_use_case
from src.presentation.api.v1.sla_dashboard import router


class SlaDashboardApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.use_case = AsyncMock()
        self.use_case.list_recent_comments.return_value = SlaDashboardCommentPage(
            comments=(), next_offset=None,
        )
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_sla_dashboard_use_case] = lambda: self.use_case
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_passes_default_and_next_offsets_and_serializes_page(self) -> None:
        for query in ("", "?offset=5", "?offset=10"):
            response = await self.client.get(
                f"/api/v1/sla-dashboard/issues/TACEA-4501/comments{query}"
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual({"comments": [], "next_offset": None}, response.json())

        self.assertEqual(
            [
                call("TACEA-4501", offset=0, limit=5),
                call("TACEA-4501", offset=5, limit=5),
                call("TACEA-4501", offset=10, limit=5),
            ],
            self.use_case.list_recent_comments.await_args_list,
        )

    async def test_rejects_negative_noninteger_and_malformed_offsets(self) -> None:
        for offset in ("-1", "1.5", "invalid"):
            with self.subTest(offset=offset):
                response = await self.client.get(
                    "/api/v1/sla-dashboard/issues/TACEA-4501/comments",
                    params={"offset": offset},
                )

                self.assertEqual(422, response.status_code)

        self.use_case.list_recent_comments.assert_not_awaited()

    async def test_passes_increasing_limits_for_latest_cumulative_comments(self) -> None:
        for limit in (5, 10, 15, 105):
            response = await self.client.get(
                "/api/v1/sla-dashboard/issues/TACEA-4501/comments",
                params={"limit": limit},
            )

            self.assertEqual(200, response.status_code)

        self.assertEqual(
            [call("TACEA-4501", offset=0, limit=limit) for limit in (5, 10, 15, 105)],
            self.use_case.list_recent_comments.await_args_list,
        )

    async def test_rejects_zero_negative_noninteger_and_malformed_limits(self) -> None:
        for limit in ("0", "-1", "1.5", "invalid"):
            with self.subTest(limit=limit):
                response = await self.client.get(
                    "/api/v1/sla-dashboard/issues/TACEA-4501/comments",
                    params={"limit": limit},
                )

                self.assertEqual(422, response.status_code)

        self.use_case.list_recent_comments.assert_not_awaited()

    async def test_reports_jira_failure_without_returning_an_empty_page(self) -> None:
        self.use_case.list_recent_comments.side_effect = RuntimeError("Jira failed")

        response = await self.client.get(
            "/api/v1/sla-dashboard/issues/TACEA-4501/comments?offset=5"
        )

        self.assertEqual(502, response.status_code)
        self.assertEqual("Jira 댓글을 불러오지 못했습니다.", response.json()["detail"])

    async def test_passes_selected_report_to_comments_and_image_requests(self) -> None:
        self.use_case.get_comment_image.return_value = JiraAttachmentContent(
            b"image", "image/png",
        )

        comments = await self.client.get(
            "/api/v1/sla-dashboard/issues/TACEA-4501/comments",
            params={"report_id": 7, "limit": 10},
        )
        image = await self.client.get(
            "/api/v1/sla-dashboard/issues/TACEA-4501/comments/10001/images/10017",
            params={"report_id": 7},
        )

        self.assertEqual(200, comments.status_code)
        self.assertEqual(200, image.status_code)
        self.assertEqual(b"image", image.content)
        self.use_case.list_recent_comments.assert_awaited_once_with(
            "TACEA-4501", offset=0, limit=10, report_id=7,
        )
        self.use_case.get_comment_image.assert_awaited_once_with(
            "TACEA-4501", "10001", "10017", report_id=7,
        )

    async def test_image_without_report_keeps_latest_report_lookup(self) -> None:
        self.use_case.get_comment_image.return_value = JiraAttachmentContent(
            b"image", "image/png",
        )

        response = await self.client.get(
            "/api/v1/sla-dashboard/issues/TACEA-4501/comments/10001/images/10017"
        )

        self.assertEqual(200, response.status_code)
        self.use_case.get_comment_image.assert_awaited_once_with(
            "TACEA-4501", "10001", "10017",
        )

    async def test_rejects_invalid_report_ids_for_comments_and_images(self) -> None:
        for suffix in ("comments", "comments/10001/images/10017"):
            for report_id in ("0", "-1", "1.5", "invalid"):
                with self.subTest(suffix=suffix, report_id=report_id):
                    response = await self.client.get(
                        f"/api/v1/sla-dashboard/issues/TACEA-4501/{suffix}",
                        params={"report_id": report_id},
                    )

                    self.assertEqual(422, response.status_code)

        self.use_case.list_recent_comments.assert_not_awaited()
        self.use_case.get_comment_image.assert_not_awaited()
