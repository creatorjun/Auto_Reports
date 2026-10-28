# backend/tests/test_cve_inventory_api.py
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from src.application.use_cases.cve_inventory import CveInventoryUseCase, CveRefreshThrottled
from src.domain.entities.cve_inventory import CveInventory
from src.presentation.api.v1.router import router


class CveInventoryApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        loader = AsyncMock()
        loader.load.return_value = CveInventory("dataset", "2026-10-22", (), 0, 0)
        self.source = AsyncMock()
        self.source.begin_refresh.return_value = None
        self.service = CveInventoryUseCase(loader, self.source)
        self.auth = SimpleNamespace(enabled=True, resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="employee")))
        self.app = FastAPI()
        self.app.state.services = SimpleNamespace(auth=self.auth, cve_inventory=self.service)
        self.app.include_router(router)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.headers = {"Authorization": "Bearer valid"}

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.service.aclose()

    async def test_all_routes_require_authentication_and_cannot_start_collection(self):
        for method, path in (("get", ""), ("get", "/packages"), ("post", "/refresh")):
            response = await getattr(self.client, method)("/api/v1/cve-inventory" + path)
            self.assertEqual(401, response.status_code)
        self.source.fetch.assert_not_awaited()
        self.source.begin_refresh.assert_not_awaited()

    async def test_snapshot_shape_no_store_and_get_without_external_calls(self):
        response = await self.client.get("/api/v1/cve-inventory", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        payload = response.json()
        self.assertEqual(7200, payload["refresh_interval_seconds"])
        self.assertEqual({"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}, payload["severity_counts"])
        self.assertEqual("dataset", payload["inventory"]["dataset_id"])
        self.source.fetch.assert_not_awaited()
        self.source.begin_refresh.assert_not_awaited()

    async def test_filters_are_validated_at_boundary(self):
        for query in ("severity=invalid", "page=0", "page_size=101", "impact=invalid", "sort=invalid"):
            response = await self.client.get("/api/v1/cve-inventory?" + query, headers=self.headers)
            self.assertEqual(422, response.status_code)
        self.assertEqual(200, (await self.client.get("/api/v1/cve-inventory?severity=unknown", headers=self.headers)).status_code)

    async def test_refresh_returns_background_state_then_cooldown(self):
        response = await self.client.post("/api/v1/cve-inventory/refresh", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["refreshing"])
        await self.service._task
        response = await self.client.post("/api/v1/cve-inventory/refresh", headers=self.headers)
        self.assertEqual(429, response.status_code)
        self.assertIn("retry-after", response.headers)

    async def test_unconfigured_service_returns_503(self):
        self.app.state.services.cve_inventory = None
        response = await self.client.get("/api/v1/cve-inventory", headers=self.headers)
        self.assertEqual(503, response.status_code)
