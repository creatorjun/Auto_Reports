# backend/tests/test_sla_digest_api.py
from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestResult
from src.presentation.api.deps import get_audit, get_auth, get_sla_digest_use_case
from src.presentation.api.v1.router import router


class SlaDigestApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.result = SlaDigestResult(
            status="sent",
            ticket_count=3,
            sla_count=5,
            recipient_count=5,
            generated_at=datetime(2026, 10, 20, 9, 0, tzinfo=KST),
        )
        self.use_case = SimpleNamespace(trigger=AsyncMock(return_value=self.result))
        self.auth = SimpleNamespace(
            enabled=True,
            resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="tester")),
        )
        self.audit = Mock()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_sla_digest_use_case] = lambda: self.use_case
        self.app.dependency_overrides[get_audit] = lambda: self.audit
        self.app.dependency_overrides[get_auth] = lambda: self.auth
        self.headers = {"Authorization": "Bearer test"}
        self.endpoint = "/api/v1/notifications/sla-digest/trigger"

    async def asyncSetUp(self) -> None:
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_omitted_body_sends_and_returns_counts_without_caching(self) -> None:
        response = await self.client.post(self.endpoint, headers=self.headers)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual(
            {
                "status": "sent",
                "ticket_count": 3,
                "sla_count": 5,
                "recipient_count": 5,
                "generated_at": "2026-10-20T09:00:00+09:00",
            },
            response.json(),
        )
        self.use_case.trigger.assert_awaited_once_with(dry_run=False)
        self.auth.resolve_access_identity.assert_awaited_once_with("test")
        self.audit.record.assert_called_once_with(
            "SLA_DIGEST_TRIGGER",
            dry_run=False,
            status="sent",
            ticket_count=3,
            sla_count=5,
            recipient_count=5,
        )

    async def test_empty_body_and_explicit_false_use_actual_delivery(self) -> None:
        for body in ({}, {"dry_run": False}):
            with self.subTest(body=body):
                self.use_case.trigger.reset_mock()
                response = await self.client.post(self.endpoint, headers=self.headers, json=body)

                self.assertEqual(200, response.status_code, response.text)
                self.assertEqual("sent", response.json()["status"])
                self.use_case.trigger.assert_awaited_once_with(dry_run=False)

    async def test_dry_run_returns_preview_and_records_preview_counts(self) -> None:
        self.use_case.trigger.return_value = replace(self.result, status="preview")

        response = await self.client.post(self.endpoint, headers=self.headers, json={"dry_run": True})

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual("preview", response.json()["status"])
        self.use_case.trigger.assert_awaited_once_with(dry_run=True)
        self.audit.record.assert_called_once_with(
            "SLA_DIGEST_TRIGGER",
            dry_run=True,
            status="preview",
            ticket_count=3,
            sla_count=5,
            recipient_count=5,
        )

    async def test_no_matches_and_already_sent_preserve_result_status(self) -> None:
        for status in ("no_matches", "already_sent"):
            with self.subTest(status=status):
                self.use_case.trigger.return_value = replace(
                    self.result, status=status, ticket_count=0, sla_count=0,
                )
                self.audit.reset_mock()
                response = await self.client.post(self.endpoint, headers=self.headers, json={})

                self.assertEqual(200, response.status_code, response.text)
                self.assertEqual("no-store", response.headers["cache-control"])
                payload = response.json()
                self.assertEqual(status, payload["status"])
                self.assertEqual((0, 0, 5), tuple(payload[key] for key in ("ticket_count", "sla_count", "recipient_count")))
                for key in ("ticket_count", "sla_count", "recipient_count"):
                    self.assertIs(type(payload[key]), int)
                self.audit.record.assert_called_once_with(
                    "SLA_DIGEST_TRIGGER",
                    dry_run=False,
                    status=status,
                    ticket_count=0,
                    sla_count=0,
                    recipient_count=5,
                )

    async def test_dry_run_requires_a_json_boolean(self) -> None:
        for value in ("true", "false", 1, 0, None, [], {}):
            with self.subTest(value=value):
                response = await self.client.post(self.endpoint, headers=self.headers, json={"dry_run": value})
                self.assertEqual(422, response.status_code, response.text)

        self.use_case.trigger.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_force_and_recipient_overrides_are_rejected(self) -> None:
        for body in (
            {"force": True},
            {"recipients": ["override@example.com"]},
            {"recipient": "override@example.com"},
            {"notify_to": ["override@example.com"]},
            {"dry_run": True, "unexpected": True},
        ):
            with self.subTest(body=body):
                response = await self.client.post(self.endpoint, headers=self.headers, json=body)
                self.assertEqual(422, response.status_code, response.text)

        self.use_case.trigger.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_missing_authentication_never_triggers_delivery(self) -> None:
        for headers in ({}, {"Authorization": "Basic dGVzdDp0ZXN0"}):
            with self.subTest(headers=headers):
                response = await self.client.post(self.endpoint, headers=headers, json={})
                self.assertEqual(401, response.status_code, response.text)

        self.use_case.trigger.assert_not_awaited()
        self.auth.resolve_access_identity.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_invalid_token_is_rejected_without_exposing_token_error(self) -> None:
        self.auth.resolve_access_identity.side_effect = ValueError("private token validation detail")

        response = await self.client.post(self.endpoint, headers=self.headers, json={})

        self.assertEqual(401, response.status_code, response.text)
        self.assertNotIn("private", response.text)
        self.use_case.trigger.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_query_tokens_cannot_authorize_email_delivery(self) -> None:
        for query in ("?token=test", "?_t=test"):
            with self.subTest(query=query):
                response = await self.client.post(self.endpoint + query, json={})
                self.assertEqual(401, response.status_code, response.text)

        self.use_case.trigger.assert_not_awaited()
        self.auth.resolve_access_identity.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_login_disabled_never_allows_guest_delivery(self) -> None:
        self.auth.enabled = False
        for headers in ({}, self.headers):
            with self.subTest(headers=headers):
                response = await self.client.post(self.endpoint, headers=headers, json={})
                self.assertEqual(401, response.status_code, response.text)

        self.use_case.trigger.assert_not_awaited()
        self.auth.resolve_access_identity.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_disabled_notification_service_returns_unavailable(self) -> None:
        del self.app.dependency_overrides[get_sla_digest_use_case]
        self.app.state.services = SimpleNamespace(notify_sla_digest=None)

        response = await self.client.post(self.endpoint, headers=self.headers, json={})

        self.assertEqual(503, response.status_code, response.text)
        self.use_case.trigger.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_configured_service_dependency_supplies_trigger_use_case(self) -> None:
        del self.app.dependency_overrides[get_sla_digest_use_case]
        self.app.state.services = SimpleNamespace(notify_sla_digest=self.use_case)
        self.use_case.trigger.return_value = replace(self.result, status="preview")

        response = await self.client.post(self.endpoint, headers=self.headers, json={"dry_run": True})

        self.assertEqual(200, response.status_code, response.text)
        self.use_case.trigger.assert_awaited_once_with(dry_run=True)

    async def test_provider_and_smtp_failures_are_private_and_audited_without_success(self) -> None:
        for dry_run, error in (
            (True, ValueError("private Jira token and upstream response")),
            (False, RuntimeError("private SMTP password and recipient@example.com")),
        ):
            with self.subTest(dry_run=dry_run, error_type=type(error).__name__):
                self.use_case.trigger.side_effect = error
                self.use_case.trigger.reset_mock()
                self.audit.reset_mock()

                response = await self.client.post(self.endpoint, headers=self.headers, json={"dry_run": dry_run})

                self.assertEqual(502, response.status_code, response.text)
                self.assertNotIn("private", response.text)
                self.assertNotIn("recipient@example.com", response.text)
                self.assertNotIn(str(error), response.text)
                self.use_case.trigger.assert_awaited_once_with(dry_run=dry_run)
                self.audit.record.assert_called_once_with(
                    "SLA_DIGEST_TRIGGER_FAILED",
                    dry_run=dry_run,
                    error_type=type(error).__name__,
                )
