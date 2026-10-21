# backend/tests/test_sla_status_api.py
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, call

import httpx
from fastapi import Depends, FastAPI, HTTPException

from src.application.use_cases.sla_status import SlaStatusSourceError
from src.domain.constants import KST
from src.domain.entities.sla_status import SlaStatusMetric, SlaStatusSnapshot, SlaStatusTicket
from src.presentation.api.deps import get_sla_status_use_case
from src.presentation.api.v1.sla_status import router


class SlaStatusApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.use_case = AsyncMock()
        self.use_case.get_snapshot.return_value = SlaStatusSnapshot(
            generated_at=datetime(2026, 10, 21, 14, 30, tzinfo=KST), threshold_percent=30,
            ticket_count=1, sla_count=2, tickets=(SlaStatusTicket(
                key="TACEA-1", summary="점검 요청", status="자료 요청 중", assignee="미지정",
                slas=(
                    SlaStatusMetric("customfield_10001", "최초 응답", 100_000, 0, 0, False),
                    SlaStatusMetric("customfield_10002", "해결", 100_000, 29_999, 29.999, True),
                ),
            ),),
        )
        self.authorized = True

        async def require_auth():
            if not self.authorized:
                raise HTTPException(status_code=401, detail="Not authenticated")

        app = FastAPI()
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_auth)])
        app.dependency_overrides[get_sla_status_use_case] = lambda: self.use_case
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_serializes_snapshot_and_exact_remaining_ratios_without_browser_cache(self) -> None:
        response = await self.client.get("/api/v1/sla-status")
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["Cache-Control"])
        payload = response.json()
        self.assertEqual("2026-10-21T14:30:00+09:00", payload["generated_at"])
        self.assertEqual((30, 1, 2), (payload["threshold_percent"], payload["ticket_count"], payload["sla_count"]))
        self.assertTrue({"key", "summary", "status", "assignee", "slas"}.issubset(payload["tickets"][0]))
        self.assertIsNone(payload["tickets"][0]["status_durations"])
        self.assertEqual("resolution_sla", payload["tickets"][0]["status_durations_basis"])
        self.assertNotIn("account_id", response.text)
        slas = payload["tickets"][0]["slas"]
        self.assertEqual(0, slas[0]["remaining_percent"])
        self.assertEqual(29.999, slas[1]["remaining_percent"])
        self.assertTrue(slas[1]["paused"])
        self.use_case.get_snapshot.assert_awaited_once_with(refresh=False)

    async def test_refresh_query_is_passed_to_shared_use_case(self) -> None:
        for suffix in ("?refresh=true", "?refresh=false"):
            self.assertEqual(200, (await self.client.get("/api/v1/sla-status" + suffix)).status_code)
        self.assertEqual([call(refresh=True), call(refresh=False)], self.use_case.get_snapshot.await_args_list)

    async def test_invalid_refresh_is_rejected_before_collection(self) -> None:
        response = await self.client.get("/api/v1/sla-status?refresh=invalid")
        self.assertEqual(422, response.status_code)
        self.use_case.get_snapshot.assert_not_awaited()

    async def test_source_failure_is_503_and_does_not_expose_upstream_details(self) -> None:
        self.use_case.get_snapshot.side_effect = SlaStatusSourceError("private Jira details")
        response = await self.client.get("/api/v1/sla-status?refresh=true")
        self.assertEqual(503, response.status_code)
        self.assertEqual("no-store", response.headers["Cache-Control"])
        self.assertEqual("Jira SLA 현황을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", response.json()["detail"])
        self.assertNotIn("private", response.text)
        self.assertNotIn("tickets", response.json())

    async def test_empty_success_is_distinct_from_failure(self) -> None:
        self.use_case.get_snapshot.return_value = SlaStatusSnapshot(
            datetime(2026, 10, 21, 14, 30, tzinfo=KST), 30, 0, 0, (),
        )
        response = await self.client.get("/api/v1/sla-status")
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json()["tickets"])
        self.assertEqual(0, response.json()["ticket_count"])

    async def test_central_auth_dependency_blocks_collection(self) -> None:
        self.authorized = False
        response = await self.client.get("/api/v1/sla-status")
        self.assertEqual(401, response.status_code)
        self.use_case.get_snapshot.assert_not_awaited()
