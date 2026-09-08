# backend/tests/test_sla_dashboard_api.py
import unittest
from unittest.mock import AsyncMock, call

import httpx
from fastapi import FastAPI

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
        for query in ("", "?offset=5"):
            response = await self.client.get(
                f"/api/v1/sla-dashboard/issues/TACEA-4501/comments{query}"
            )

            self.assertEqual(200, response.status_code)
            self.assertEqual({"comments": [], "next_offset": None}, response.json())

        self.assertEqual(
            [call("TACEA-4501", offset=0), call("TACEA-4501", offset=5)],
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

    async def test_reports_jira_failure_without_returning_an_empty_page(self) -> None:
        self.use_case.list_recent_comments.side_effect = RuntimeError("Jira failed")

        response = await self.client.get(
            "/api/v1/sla-dashboard/issues/TACEA-4501/comments?offset=5"
        )

        self.assertEqual(502, response.status_code)
        self.assertEqual("Jira 댓글을 불러오지 못했습니다.", response.json()["detail"])
