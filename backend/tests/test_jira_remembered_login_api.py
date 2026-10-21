# backend/tests/test_jira_remembered_login_api.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import Depends, FastAPI

from src.application.ports.jira_login_port import JiraLoginPort
from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort, JiraPersistentGrant
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.ports.personal_data_port import PersonalDataProfilePort
from src.application.services.auth_service import AuthService
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.config.settings import Settings
from src.infrastructure.security.jwt_service import JwtService
from src.presentation.api.v1.auth import JIRA_DEVICE_COOKIE, JIRA_STATE_COOKIE, router
from src.presentation.api.v1.deps import require_auth


class JiraRememberedLoginApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings(
            _env_file=None, jira_base_url="https://company.atlassian.net", jira_email="service@example.test",
            jira_api_token="fixture", LOGIN=True, JWT_SECRET="persistent-login-test-secret-32-bytes", COOKIE_SECURE=True,
        )
        self.identity = AuthIdentity(
            "jira:cloud-123:account:123", "사용자", "jira",
            int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp()), 1, "s" * 43,
        )
        self.oauth = Mock(spec=JiraOAuthPort)
        self.oauth.authorization_url.side_effect = lambda state, **kwargs: f"https://auth.atlassian.com/authorize?state={state}"
        self.grant = JiraUserGrant("cloud-123", "account:123", "private-access", datetime.now(timezone.utc) + timedelta(hours=1), "private-refresh")
        self.oauth.authenticate_persistent = AsyncMock(return_value=JiraPersistentGrant(self.identity, self.grant))
        self.profiles = AsyncMock(spec=PersonalDataProfilePort)
        self.profiles.register_identity.side_effect = lambda identity: identity
        self.profiles.resolve_identity.side_effect = lambda identity: identity
        self.login = AsyncMock(spec=JiraLoginPort)
        self.login.finish_login.return_value = (self.identity, "d" * 43)
        self.login.resume.return_value = self.identity
        self.login.resolve.side_effect = lambda identity: identity
        self.login.has_device.return_value = True
        self.auth = AuthService(
            JwtService(self.settings), True, "admin", "password", "root", "root-password", 7, True,
            jira_oauth=self.oauth, personal_data=self.profiles, jira_grants=self.login, jira_login=self.login,
        )
        self.audit = Mock()
        self.app = FastAPI()
        self.app.state.services = SimpleNamespace(auth=self.auth, audit=self.audit)
        self.app.include_router(router, prefix="/api/v1")

        @self.app.get("/protected")
        async def protected(username: str = Depends(require_auth)):
            return {"username": username}

    def client(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="https://test")

    async def first_login(self, client):
        started = await client.post("/api/v1/auth/jira/start")
        self.assertEqual(200, started.status_code)
        state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
        self.oauth.authorization_url.assert_called_with(state, include_offline=True)
        result = await client.get("/api/v1/auth/jira/callback", params={"state": state, "code": "code"})
        self.assertEqual(303, result.status_code)
        return result

    async def test_first_consent_persists_connection_but_no_provider_tokens_reach_browser(self):
        async with self.client() as client:
            result = await self.first_login(client)
            self.assertEqual("/login?jira=success", result.headers["location"])
            self.assertEqual("d" * 43, client.cookies[JIRA_DEVICE_COOKIE])
            device_cookie = next(value for value in result.headers.get_list("set-cookie") if value.startswith(JIRA_DEVICE_COOKIE + "="))
            for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth", "Max-Age=7776000"):
                self.assertIn(flag, device_cookie)
            self.assertNotIn("private-access", str(result.headers))
            self.assertNotIn("private-refresh", str(result.headers))
            self.login.finish_login.assert_awaited_once_with(self.grant, self.identity, None)
            self.oauth.authenticate.assert_not_called()

    async def test_logout_keeps_remembered_connection_but_relogin_requires_explicit_post(self):
        async with self.client() as client:
            await self.first_login(client)
            refreshed = await client.post("/api/v1/auth/refresh")
            token = refreshed.json()["access_token"]
            self.assertEqual(200, (await client.get("/protected", headers={"Authorization": f"Bearer {token}"})).status_code)
            await client.post("/api/v1/auth/logout")
            self.login.revoke.assert_awaited_once()
            self.login.resolve.side_effect = ValueError("Logged out session")
            self.assertIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.assertNotIn("refresh_token", client.cookies)
            self.assertEqual(401, (await client.get("/protected", headers={"Authorization": f"Bearer {token}"})).status_code)
            self.assertEqual(401, (await client.post("/api/v1/auth/refresh")).status_code)
            providers = await client.get("/api/v1/auth/providers")
            self.assertEqual({"enabled": True, "remembered": True}, providers.json()["jira"])
            self.assertEqual("no-store", providers.headers["cache-control"])
            self.login.resume.assert_not_awaited()
            self.oauth.authorization_url.reset_mock()
            login = await client.post("/api/v1/auth/jira/start")
            self.assertEqual({"authorization_url": "/login?jira=success"}, login.json())
            self.login.resume.assert_awaited_once_with("d" * 43)
            self.oauth.authorization_url.assert_not_called()
            self.assertIn("refresh_token", client.cookies)

    async def test_unknown_device_requires_authorization_without_accepting_body_identity(self):
        self.login.resume.side_effect = JiraLoginDenied("Unknown device")
        async with self.client() as client:
            client.cookies.set(JIRA_DEVICE_COOKIE, "unknown", path="/api/v1/auth")
            response = await client.post("/api/v1/auth/jira/start", json={"account_id": "account:123"})
            self.assertEqual(200, response.status_code)
            self.assertTrue(response.json()["authorization_url"].startswith("https://auth.atlassian.com/"))
            self.assertNotIn("refresh_token", client.cookies)

    async def test_temporary_provider_failure_preserves_connection_without_new_consent(self):
        self.login.resume.side_effect = JiraLoginUnavailable("Provider unavailable")
        async with self.client() as client:
            client.cookies.set(JIRA_DEVICE_COOKIE, "d" * 43, path="/api/v1/auth")
            response = await client.post("/api/v1/auth/jira/start")
            self.assertEqual(503, response.status_code)
            self.assertIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.oauth.authorization_url.assert_not_called()
            self.login.forget.assert_not_awaited()

    async def test_account_switch_forgets_device_and_requests_a_new_consent(self):
        async with self.client() as client:
            await self.first_login(client)
            self.oauth.authorization_url.reset_mock()
            response = await client.post("/api/v1/auth/jira/start", json={"force_authorization": True})
            self.assertEqual(200, response.status_code)
            self.login.forget.assert_awaited_once_with("d" * 43)
            self.login.resume.assert_not_awaited()
            self.assertNotIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.assertNotIn("refresh_token", client.cookies)
            self.oauth.authorization_url.assert_called_once()

    async def test_forget_connection_clears_cookies_and_is_same_origin_only(self):
        async with self.client() as client:
            await self.first_login(client)
            blocked = await client.post("/api/v1/auth/jira/forget", headers={"Origin": "https://evil.example"})
            self.assertEqual(403, blocked.status_code)
            self.login.forget.assert_not_awaited()
            result = await client.post("/api/v1/auth/jira/forget")
            self.assertEqual(200, result.status_code)
            self.login.forget.assert_awaited_once_with("d" * 43)
            self.assertNotIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.assertNotIn("refresh_token", client.cookies)

    async def test_forget_cancels_pending_authorization_even_if_the_old_state_cookie_is_replayed(self):
        async with self.client() as client:
            started = await client.post("/api/v1/auth/jira/start")
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            forgotten = await client.post("/api/v1/auth/jira/forget")
            self.assertEqual(200, forgotten.status_code)
            self.assertNotIn(JIRA_STATE_COOKIE, client.cookies)
            self.assertNotIn(state, self.auth._jira_states)
            callback = await client.get(
                "/api/v1/auth/jira/callback", params={"state": state, "code": "old-code"},
                headers={"Cookie": f"{JIRA_STATE_COOKIE}={state}"},
            )
            self.assertEqual("/login?jira=denied", callback.headers["location"])
            self.assertNotIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.assertNotIn("refresh_token", client.cookies)
        self.oauth.authenticate_persistent.assert_not_awaited()
        self.login.finish_login.assert_not_awaited()

    async def test_account_switch_cancels_pending_authorization_and_keeps_new_state_after_late_callback(self):
        async with self.client() as client:
            started = await client.post("/api/v1/auth/jira/start")
            old_state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            switched = await client.post("/api/v1/auth/jira/start", json={"force_authorization": True})
            new_state = parse_qs(urlsplit(switched.json()["authorization_url"]).query)["state"][0]
            self.assertNotEqual(old_state, new_state)
            callback = await client.get(
                "/api/v1/auth/jira/callback", params={"state": old_state, "code": "old-code"},
                headers={"Cookie": f"{JIRA_STATE_COOKIE}={old_state}"},
            )
            self.assertEqual("/login?jira=denied", callback.headers["location"])
            self.assertEqual(new_state, client.cookies[JIRA_STATE_COOKIE])
            self.oauth.authenticate_persistent.assert_not_awaited()
            fresh = await client.get("/api/v1/auth/jira/callback", params={"state": new_state, "code": "new-code"})
            self.assertEqual("/login?jira=success", fresh.headers["location"])
            self.oauth.authenticate_persistent.assert_awaited_once_with("new-code")

    async def _cancel_inflight_callback(self, stage, switch_account=False):
        entered, release = asyncio.Event(), asyncio.Event()
        operation, result = {
            "exchange": (self.oauth.authenticate_persistent, JiraPersistentGrant(self.identity, self.grant)),
            "profile": (self.profiles.register_identity, self.identity),
            "finish": (self.login.finish_login, (self.identity, "d" * 43)),
        }[stage]

        async def delayed(*args):
            entered.set()
            await release.wait()
            return result

        operation.side_effect = delayed
        async with self.client() as client:
            started = await client.post("/api/v1/auth/jira/start")
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            callback = asyncio.create_task(client.get("/api/v1/auth/jira/callback", params={"state": state, "code": "code"}))
            try:
                await asyncio.wait_for(entered.wait(), 1)
                if switch_account:
                    changed = await client.post("/api/v1/auth/jira/start", json={"force_authorization": True})
                    new_state = parse_qs(urlsplit(changed.json()["authorization_url"]).query)["state"][0]
                else:
                    changed = await client.post("/api/v1/auth/jira/forget")
                self.assertEqual(200, changed.status_code)
                release.set()
                completed = await asyncio.wait_for(callback, 1)
                self.assertEqual("/login?jira=denied", completed.headers["location"])
                self.assertNotIn(JIRA_DEVICE_COOKIE, client.cookies)
                self.assertNotIn("refresh_token", client.cookies)
                if switch_account:
                    self.assertEqual(new_state, client.cookies[JIRA_STATE_COOKIE])
                    self.assertIn(new_state, self.auth._jira_states)
                else:
                    self.assertNotIn(JIRA_STATE_COOKIE, client.cookies)
            finally:
                release.set()
                callback.cancel()
                await asyncio.gather(callback, return_exceptions=True)
        if stage == "exchange":
            self.profiles.register_identity.assert_not_awaited()
        if stage != "finish":
            self.login.finish_login.assert_not_awaited()
            self.login.forget.assert_not_awaited()
        else:
            self.login.forget.assert_awaited_once_with("d" * 43)

    async def test_forget_during_code_exchange_cancels_before_profile_or_device_creation(self):
        await self._cancel_inflight_callback("exchange")

    async def test_forget_during_profile_registration_cancels_before_device_creation(self):
        await self._cancel_inflight_callback("profile")

    async def test_forget_during_device_creation_revokes_the_late_device_and_session(self):
        await self._cancel_inflight_callback("finish")

    async def test_switch_during_device_creation_revokes_late_device_without_clearing_new_authorization(self):
        await self._cancel_inflight_callback("finish", switch_account=True)

    async def test_forget_request_with_pre_callback_cookies_revokes_the_completed_device(self):
        async with self.client() as client:
            started = await client.post("/api/v1/auth/jira/start")
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            callback = await client.get("/api/v1/auth/jira/callback", params={"state": state, "code": "code"})
            self.assertEqual("/login?jira=success", callback.headers["location"])
            self.assertNotIn(JIRA_STATE_COOKIE, client.cookies)
            forgotten = await client.post(
                "/api/v1/auth/jira/forget", headers={"Cookie": f"{JIRA_STATE_COOKIE}={state}"},
            )
            self.assertEqual(200, forgotten.status_code)
            self.login.forget.assert_awaited_once_with("d" * 43)
            self.assertNotIn(JIRA_DEVICE_COOKIE, client.cookies)
            self.assertNotIn("refresh_token", client.cookies)

    async def test_cross_site_forget_cannot_cancel_pending_authorization(self):
        async with self.client() as client:
            started = await client.post("/api/v1/auth/jira/start")
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            blocked = await client.post("/api/v1/auth/jira/forget", headers={"Origin": "https://evil.example"})
            self.assertEqual(403, blocked.status_code)
            self.assertIn(state, self.auth._jira_states)
            callback = await client.get("/api/v1/auth/jira/callback", params={"state": state, "code": "code"})
            self.assertEqual("/login?jira=success", callback.headers["location"])
            self.login.forget.assert_not_awaited()

    async def test_employee_cancellation_does_not_cancel_owner_privacy_authorization(self):
        state, _ = self.auth.begin_jira_login(privacy_generation=7)
        await self.auth.cancel_jira_login(state)
        self.assertEqual(7, self.auth.consume_jira_state(state, state))
        self.login.forget.assert_not_awaited()

    async def test_completed_attempt_is_retained_for_ten_minutes_then_reclaimed(self):
        with patch("src.application.services.auth_service.monotonic", return_value=100):
            state, _ = self.auth.begin_jira_login()
            self.auth.consume_jira_state(state, state)
            await self.auth.complete_jira_login("code", None, state=state)
        with patch("src.application.services.auth_service.monotonic", return_value=699):
            self.auth.begin_jira_login()
            self.assertIn(state, self.auth._jira_attempts)
        with patch("src.application.services.auth_service.monotonic", return_value=701):
            self.auth.begin_jira_login()
            self.assertNotIn(state, self.auth._jira_attempts)

    async def test_reconciliation_is_account_scoped_instead_of_clearing_all_connections(self):
        await self.auth.clear_jira_grants()
        self.login.reconcile_privacy.assert_awaited_once()
        self.login.clear.assert_not_awaited()

    async def test_access_and_refresh_resolution_enforce_persistent_session_state(self):
        self.login.resolve.side_effect = ValueError("Revoked session")
        for token, resolver in (
            (self.auth.create_identity_access_token(self.identity), self.auth.resolve_access_identity),
            (self.auth.create_identity_refresh_token(self.identity), self.auth.resolve_refresh_identity),
        ):
            with self.assertRaises(ValueError):
                await resolver(token)


if __name__ == "__main__":
    unittest.main()
