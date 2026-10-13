# backend/tests/test_c_level_api.py
import unittest
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from src.application.use_cases.c_level_workspace import CLevelPreviewExpiredError
from src.domain.entities.c_level_history import CLevelComment, CLevelSnapshotSummary
from src.presentation.api.deps import get_audit
from src.presentation.api.v1.c_level_report import get_c_level_workspace, router
from src.presentation.api.v1.deps import require_auth


class CLevelApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.use_case = AsyncMock()
        self.audit = Mock()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_c_level_workspace] = lambda: self.use_case
        app.dependency_overrides[require_auth] = lambda: "engineer"
        app.dependency_overrides[get_audit] = lambda: self.audit
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_query_validation_and_missing_values(self) -> None:
        self.use_case.get_report.return_value = {"sla": {"rate": None}, "report_token": "token"}
        response = await self.client.get("/api/v1/c-level-report?period=month&date=2026-10-12")
        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.json()["sla"]["rate"])
        self.assertEqual("no-store", response.headers["cache-control"])
        for query in ("period=year", "date=2026-02-30"):
            self.assertEqual(422, (await self.client.get(f"/api/v1/c-level-report?{query}")).status_code)

    async def test_snapshot_rejects_client_supplied_values_or_identity(self) -> None:
        for extra in ({"payload": {"count": 999}}, {"saved_by": "admin"}):
            response = await self.client.post("/api/v1/c-level-report/snapshots", json={"report_token": "a" * 32, **extra})
            self.assertEqual(422, response.status_code)
        self.use_case.save_snapshot.assert_not_awaited()

    async def test_expired_preview_has_actionable_error(self) -> None:
        self.use_case.save_snapshot.side_effect = CLevelPreviewExpiredError("다시 조회해 주세요.")
        response = await self.client.post("/api/v1/c-level-report/snapshots", json={"report_token": "a" * 32})
        self.assertEqual(410, response.status_code)
        self.assertEqual("다시 조회해 주세요.", response.json()["detail"])

    async def test_save_uses_authenticated_identity(self) -> None:
        self.use_case.save_comment.return_value = CLevelComment("TACEA-3340", updated_by="engineer")
        response = await self.client.put("/api/v1/c-level-report/comments/TACEA-3340", json={"report_token": "a" * 32, "delay_reason": "확인 중"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("engineer", self.use_case.save_comment.await_args.args[-1])
        self.assertEqual("engineer", response.json()["updated_by"])

    async def test_snapshot_creation_and_list_bounds(self) -> None:
        summary = CLevelSnapshotSummary(3, "주간 보고", "week", "2026-10-06", "2026-10-12", "2026-10-13T00:00:00+09:00", "engineer", "2026-10-13T01:00:00Z")
        self.use_case.save_snapshot.return_value = summary
        response = await self.client.post("/api/v1/c-level-report/snapshots", json={"report_token": "a" * 32})
        self.assertEqual(201, response.status_code)
        self.assertEqual(3, response.json()["id"])
        for query in ("limit=101", "limit=0", "offset=-1"):
            self.assertEqual(422, (await self.client.get(f"/api/v1/c-level-report/snapshots?{query}")).status_code)
