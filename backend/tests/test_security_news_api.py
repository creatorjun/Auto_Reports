# backend/tests/test_security_news_api.py
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from src.application.use_cases.security_news import SecurityNewsRefreshThrottled
from src.domain.entities.security_news import SecurityNewsItem, SecurityNewsSnapshot
from src.domain.entities.security_news_translation import NewsTranslationState
from src.presentation.api.v1.router import router


class SecurityNewsApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.use_case = AsyncMock()
        self.use_case.get_snapshot.return_value = SecurityNewsSnapshot(
            (), (), True, False, datetime(2026, 10, 20, tzinfo=timezone.utc), None, 86400,
        )
        self.auth = SimpleNamespace(enabled=True, resolve_access_identity=AsyncMock(
            return_value=SimpleNamespace(username="employee"),
        ))
        self.app = FastAPI()
        self.app.state.services = SimpleNamespace(auth=self.auth, security_news=self.use_case)
        self.app.include_router(router)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_unauthenticated_reads_and_refreshes_cannot_start_collection(self) -> None:
        self.assertEqual(401, (await self.client.get("/api/v1/security-news")).status_code)
        self.assertEqual(401, (await self.client.post("/api/v1/security-news/refresh")).status_code)
        self.use_case.get_snapshot.assert_not_awaited()

    async def test_authenticated_snapshot_is_serialized_without_http_caching(self) -> None:
        response = await self.client.get("/api/v1/security-news", headers={"Authorization": "Bearer valid"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual("2026-10-20T00:00:00Z", response.json()["refreshed_at"])
        self.assertEqual(86400, response.json()["refresh_interval_seconds"])
        self.assertEqual(0, response.json()["retry_after_seconds"])
        self.use_case.get_snapshot.assert_awaited_once_with(refresh=False)

    async def test_manual_refresh_uses_same_authenticated_service(self) -> None:
        response = await self.client.post("/api/v1/security-news/refresh", headers={"Authorization": "Bearer valid"})
        self.assertEqual(200, response.status_code)
        self.use_case.get_snapshot.assert_awaited_once_with(refresh=True)

    async def test_translations_keep_original_text_and_independent_progress(self) -> None:
        self.use_case.get_snapshot.return_value = SecurityNewsSnapshot(
            items=(SecurityNewsItem(
                id="article-1", source_id="nvd", kind="cve",
                title="Security update", summary="Apply the update.",
                title_ko="보안 업데이트", summary_ko="업데이트를 적용하세요.",
                url="https://nvd.nist.gov/", cve_ids=("CVE-2026-12345",),
            ),),
            sources=(), initialized=True, refreshing=False, refreshed_at=None,
            next_refresh_at=None, refresh_interval_seconds=86400,
            translation=NewsTranslationState(
                enabled=True, translating=True, translated_count=1, pending_count=2,
            ),
        )
        response = await self.client.get("/api/v1/security-news", headers={"Authorization": "Bearer valid"})
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("Security update", payload["items"][0]["title"])
        self.assertEqual("보안 업데이트", payload["items"][0]["title_ko"])
        self.assertEqual("Apply the update.", payload["items"][0]["summary"])
        self.assertEqual("업데이트를 적용하세요.", payload["items"][0]["summary_ko"])
        self.assertEqual(["CVE-2026-12345"], payload["items"][0]["cve_ids"])
        self.assertFalse(payload["refreshing"])
        self.assertEqual({
            "enabled": True, "translating": True, "translated_count": 1,
            "pending_count": 2, "message": None,
        }, payload["translation"])

    async def test_throttle_returns_retry_after_and_keeps_no_store(self) -> None:
        self.use_case.get_snapshot.side_effect = SecurityNewsRefreshThrottled(42)
        response = await self.client.post("/api/v1/security-news/refresh", headers={"Authorization": "Bearer valid"})
        self.assertEqual(429, response.status_code)
        self.assertEqual("42", response.headers["retry-after"])
        self.assertEqual("no-store", response.headers["cache-control"])

    async def test_unconfigured_service_returns_503_without_http_caching(self) -> None:
        self.app.state.services.security_news = None
        response = await self.client.get("/api/v1/security-news", headers={"Authorization": "Bearer valid"})
        self.assertEqual(503, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
