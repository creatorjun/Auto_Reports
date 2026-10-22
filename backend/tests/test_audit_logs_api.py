# backend/tests/test_audit_logs_api.py
import unittest
from datetime import date
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI, HTTPException

from src.application.ports.audit_log_reader_port import AuditLogReadError
from src.domain.entities.audit_log import AuditLogEntry, AuditLogPage
from src.presentation.api.deps import get_audit_logs
from src.presentation.api.v1.audit_logs import router
from src.presentation.api.v1.deps import require_superadmin


class AuditLogsApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.use_case = AsyncMock()
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.app.dependency_overrides[get_audit_logs] = lambda: self.use_case
        self.app.dependency_overrides[require_superadmin] = lambda: "root"
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_filters_and_missing_identity_are_returned_without_caching(self) -> None:
        self.use_case.execute.return_value = AuditLogPage([AuditLogEntry("2026-10-13T09:00:00+09:00", "REPORT_DELETE", None, None, {"report_id": "3"})], 1, 50, 0, ["REPORT_DELETE"], [])
        response = await self.client.get("/api/v1/audit-logs?start_date=2026-10-01&end_date=2026-10-13&event=REPORT_DELETE&search=report")
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertIsNone(response.json()["items"][0]["username"])
        query = self.use_case.execute.await_args.args[0]
        self.assertEqual(date(2026, 10, 1), query.start_date)
        self.assertEqual(date(2026, 10, 13), query.end_date)
        self.assertEqual("REPORT_DELETE", query.event)

    async def test_forbidden_requests_never_read_logs(self) -> None:
        def forbidden() -> None:
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

        self.app.dependency_overrides[require_superadmin] = forbidden
        response = await self.client.get("/api/v1/audit-logs")
        self.assertEqual(403, response.status_code)
        self.use_case.execute.assert_not_awaited()

    async def test_jira_display_name_and_email_are_returned_with_original_principal(self) -> None:
        self.use_case.execute.return_value = AuditLogPage([
            AuditLogEntry("2026-10-13T09:00:00+09:00", "REPORT_DELETE", "jira:site:account", None, {}, "홍길동", "hong@example.com"),
        ], 1, 50, 0)
        response = await self.client.get("/api/v1/audit-logs")
        self.assertEqual(200, response.status_code)
        entry = response.json()["items"][0]
        self.assertEqual("jira:site:account", entry["username"])
        self.assertEqual("홍길동", entry["display_name"])
        self.assertEqual("hong@example.com", entry["email_address"])

    async def test_query_shape_is_validated_before_reading(self) -> None:
        for query in ("start_date=2026-02-30", "limit=101", "limit=0", "offset=-1", "offset=10000", "search=" + "x" * 201):
            self.assertEqual(422, (await self.client.get(f"/api/v1/audit-logs?{query}")).status_code)
        self.use_case.execute.assert_not_awaited()

    async def test_reader_failure_is_not_a_successful_empty_page(self) -> None:
        self.use_case.execute.side_effect = AuditLogReadError("감사 로그 파일을 읽을 수 없습니다.")
        response = await self.client.get("/api/v1/audit-logs")
        self.assertEqual(503, response.status_code)
        self.assertIn("읽을 수 없습니다", response.json()["detail"])

    async def test_invalid_date_order_returns_actionable_validation_error(self) -> None:
        self.use_case.execute.side_effect = ValueError("시작일은 종료일보다 늦을 수 없습니다.")
        response = await self.client.get("/api/v1/audit-logs?start_date=2026-10-13&end_date=2026-10-01")
        self.assertEqual(422, response.status_code)
        self.assertIn("시작일", response.json()["detail"])
