# backend/tests/test_sla_violation_api.py
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from src.application.errors import EntityNotFoundError
from src.application.use_cases.sla_violation_report import (
    SlaViolationGenerationInProgressError,
    SlaViolationReportUseCase,
    SlaViolationSourceError,
)
from src.presentation.api.deps import get_audit, get_auth
from src.presentation.api.v1.deps import get_sla_violation_use_case
from src.presentation.api.v1.router import router
from tests.test_sla_violation_workflow import sample_report


class SlaViolationApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.use_case = AsyncMock(spec=SlaViolationReportUseCase)
        self.report = replace(sample_report(), id=5)
        self.use_case.generate.return_value = self.report
        self.use_case.get_latest.return_value = self.report
        self.use_case.get_by_id.return_value = self.report
        self.use_case.list_summaries.return_value = [self.report]
        self.audit = Mock()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_sla_violation_use_case] = lambda: self.use_case
        self.app.dependency_overrides[get_audit] = lambda: self.audit
        self.app.dependency_overrides[get_auth] = lambda: SimpleNamespace(enabled=True, decode_access_token=lambda token: "tester")
        self.headers = {"Authorization": "Bearer test"}
        self.endpoint = "/api/v1/sla-violations"

    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_all_routes_require_authentication(self) -> None:
        for method, path in (("POST", ""), ("GET", "/latest"), ("GET", "/history"), ("GET", "/5")):
            with self.subTest(path=path):
                response = await self.client.request(method, self.endpoint + path)
                self.assertEqual(401, response.status_code)
        self.use_case.generate.assert_not_awaited()
        self.use_case.get_latest.assert_not_awaited()

    async def test_create_returns_saved_report_and_audits_actor_and_counts(self) -> None:
        response = await self.client.post(self.endpoint, headers=self.headers, json={"period": "month", "date": "2026-10-14"})
        self.assertEqual(201, response.status_code, response.text)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.use_case.generate.assert_awaited_once_with(period="month", selected_date=date(2026, 10, 14), generated_by="tester")
        payload = response.json()
        self.assertEqual((5, 1, 1), (payload["id"], payload["initial_response_count"], payload["resolution_count"]))
        ticket = payload["tickets"][0]
        self.assertEqual([], ticket["partners"])
        self.assertIsNone(ticket["breaches"][1]["breached_at"])
        self.assertEqual("TAC 담당자", ticket["tac_assignee"])
        self.audit.record.assert_called_once_with(
            "SLA_VIOLATION_REPORT_CREATE", report_id=5, period="month", selected_date="2026-10-14",
            ticket_count=1, initial_response_count=1, resolution_count=1,
        )

    async def test_latest_returns_full_snapshot_or_null(self) -> None:
        response = await self.client.get(self.endpoint + "/latest", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual(13, response.json()["tickets"][0]["elapsed_days"])
        self.use_case.get_latest.return_value = None
        response = await self.client.get(self.endpoint + "/latest", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.json())

    async def test_history_excludes_ticket_payload_and_passes_pagination(self) -> None:
        response = await self.client.get(self.endpoint + "/history?limit=7&offset=3", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.use_case.list_summaries.assert_awaited_once_with(limit=7, offset=3)
        self.assertEqual(5, response.json()[0]["id"])
        self.assertNotIn("tickets", response.json()[0])
        self.assertNotIn("warnings", response.json()[0])

    async def test_saved_report_missing_is_404(self) -> None:
        self.use_case.get_by_id.side_effect = EntityNotFoundError("report", 9)
        response = await self.client.get(self.endpoint + "/9", headers=self.headers)
        self.assertEqual(404, response.status_code)

    async def test_request_validation_rejects_invalid_period_date_and_pagination(self) -> None:
        for body in (
            {"period": "day", "date": "2026-10-14"},
            {"period": "month", "date": "bad-date"},
            {"period": "month", "date": "2026-10-14", "unexpected": True},
        ):
            with self.subTest(body=body):
                response = await self.client.post(self.endpoint, headers=self.headers, json=body)
                self.assertEqual(422, response.status_code)
        for path in ("/history?limit=0", "/history?limit=101", "/history?offset=-1", "/0"):
            with self.subTest(path=path):
                response = await self.client.get(self.endpoint + path, headers=self.headers)
                self.assertEqual(422, response.status_code)
        self.use_case.generate.assert_not_awaited()

    async def test_failure_responses_never_record_success_or_expose_upstream_detail(self) -> None:
        for error, status in (
            (SlaViolationGenerationInProgressError(), 409),
            (SlaViolationSourceError("private upstream token"), 502),
            (ValueError("미래 날짜의 보고서는 생성할 수 없습니다."), 422),
        ):
            with self.subTest(status=status):
                self.use_case.generate.side_effect = error
                response = await self.client.post(self.endpoint, headers=self.headers, json={"period": "month", "date": "2026-10-14"})
                self.assertEqual(status, response.status_code)
                self.assertNotIn("private", response.text)
        self.audit.record.assert_not_called()
