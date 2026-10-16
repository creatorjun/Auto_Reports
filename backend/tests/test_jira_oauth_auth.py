# backend/tests/test_jira_oauth_auth.py
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import Depends, FastAPI
from jose import jwt

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort, JiraReportingGrant
from src.application.ports.personal_data_port import PersonalDataProfilePort, PersonalDataReportingPort
from src.application.services.auth_service import AuthService
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.jira_oauth_client import JiraOAuthClient
from src.infrastructure.security.jwt_service import JwtService
from src.presentation.api.v1.auth import JIRA_STATE_COOKIE, router
from src.presentation.api.v1.deps import require_auth, require_superadmin


def settings() -> Settings:
    return Settings(
        _env_file=None, jira_base_url="https://company.atlassian.net",
        jira_email="service@example.test", jira_api_token="service-token",
        LOGIN=True, ADMIN="admin", ADMIN_PASSWORD="admin-password",
        SUPERADMIN="superadmin", SUPERADMIN_PASSWORD="superadmin-password",
        JWT_SECRET="test-secret-only",
    )


class JiraOAuthClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.resources = [{
            "id": "cloud-123", "url": "https://company.atlassian.net",
            "scopes": ["read:jira-user", "read:jira-work"],
        }]
        self.profile = {
            "accountId": "account:123", "displayName": "superadmin",
            "active": True, "accountType": "atlassian",
        }
        self.permissions = {"permissions": {"BROWSE_PROJECTS": {"havePermission": True}}}
        self.status = {}

    def handle(self, request):
        self.requests.append(request)
        path = request.url.path
        if path in self.status:
            return httpx.Response(self.status[path], json={"error": "secret error details"})
        if path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "upstream-sensitive-token", "refresh_token": "private-owner-refresh"})
        if path == "/oauth/token/accessible-resources":
            return httpx.Response(200, json=self.resources)
        if path.endswith("/myself"):
            return httpx.Response(200, json=self.profile)
        if path.endswith("/mypermissions"):
            return httpx.Response(200, json=self.permissions)
        raise AssertionError(path)

    def adapter(self, transport=None):
        return JiraOAuthClient(
            "client-id", "client-secret", "http://test/api/v1/auth/jira/callback",
            "https://company.atlassian.net", "TACEA",
            transport=transport or httpx.MockTransport(self.handle),
        )

    async def test_exact_site_identity_and_project_permission_are_verified(self):
        identity = await self.adapter().authenticate("authorization-code")
        self.assertEqual(AuthIdentity("jira:cloud-123:account:123", "superadmin", "jira"), identity)
        self.assertEqual(4, len(self.requests))
        self.assertEqual("auth.atlassian.com", self.requests[0].url.host)
        self.assertEqual("authorization-code", json.loads(self.requests[0].content)["code"])
        self.assertEqual("client-secret", json.loads(self.requests[0].content)["client_secret"])
        for request in self.requests[1:]:
            self.assertEqual("api.atlassian.com", request.url.host)
            self.assertEqual("Bearer upstream-sensitive-token", request.headers["authorization"])
            self.assertNotIn("upstream-sensitive-token", str(request.url))
        self.assertEqual("TACEA", self.requests[-1].url.params["projectKey"])
        self.assertEqual("BROWSE_PROJECTS", self.requests[-1].url.params["permissions"])

    def test_authorization_uses_read_only_scopes_and_exact_callback(self):
        url = self.adapter().authorization_url("browser-state")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual("auth.atlassian.com", urlsplit(url).hostname)
        self.assertEqual(["read:jira-user read:jira-work"], query["scope"])
        self.assertEqual(["browser-state"], query["state"])
        self.assertEqual(["http://test/api/v1/auth/jira/callback"], query["redirect_uri"])
        self.assertNotIn("client-secret", url)
        self.assertNotIn("offline_access", url)

    async def test_offline_access_is_requested_only_for_reporting_owner(self):
        adapter = self.adapter()
        query = parse_qs(urlsplit(adapter.authorization_url("owner-state", include_offline=True)).query)
        self.assertEqual(["read:jira-user read:jira-work offline_access"], query["scope"])
        grant = await adapter.authenticate_reporting_owner("code")
        self.assertEqual("private-owner-refresh", grant.refresh_token)
        self.assertNotIn("private-owner-refresh", repr(grant))
        self.assertEqual("jira:cloud-123:account:123", grant.identity.username)

    async def test_other_site_or_missing_scope_is_denied_before_profile(self):
        for resources in (
            [{**self.resources[0], "url": "https://other.atlassian.net"}],
            [{**self.resources[0], "url": "https://company.atlassian.net.attacker.test"}],
            [{**self.resources[0], "scopes": ["read:jira-user"]}],
            [],
            {"invalid": True},
        ):
            with self.subTest(resources=resources):
                self.resources = resources
                self.requests.clear()
                with self.assertRaises(JiraLoginDenied):
                    await self.adapter().authenticate("code")
                self.assertEqual(2, len(self.requests))

    async def test_disabled_customer_app_or_missing_identity_is_denied(self):
        for overrides in (
            {"active": False}, {"active": "true"}, {"accountType": "customer"},
            {"accountType": "app"}, {"accountId": ""}, {"accountId": "../../admin"},
        ):
            with self.subTest(overrides=overrides):
                original = self.profile.copy()
                self.profile.update(overrides)
                with self.assertRaises(JiraLoginDenied):
                    await self.adapter().authenticate("code")
                self.profile = original

    async def test_project_permission_must_be_explicitly_true(self):
        for permissions in ({}, {"permissions": {}}, {"permissions": {"BROWSE_PROJECTS": {"havePermission": False}}}):
            self.permissions = permissions
            with self.assertRaises(JiraLoginDenied):
                await self.adapter().authenticate("code")

    async def test_upstream_auth_failures_do_not_expose_payload(self):
        for code in (400, 401, 403, 302):
            self.status["/oauth/token"] = code
            with self.assertRaises(JiraLoginDenied) as failure:
                await self.adapter().authenticate("sensitive-code")
            self.assertNotIn("secret", str(failure.exception))
            self.assertNotIn("sensitive-code", str(failure.exception))

    async def test_rate_limit_server_failure_and_timeout_are_unavailable(self):
        for code in (429, 500, 503):
            self.status["/oauth/token"] = code
            with self.assertRaises(JiraLoginUnavailable):
                await self.adapter().authenticate("code")
        def timeout(request):
            raise httpx.ReadTimeout("sensitive provider request", request=request)
        with self.assertRaises(JiraLoginUnavailable) as failure:
            await self.adapter(httpx.MockTransport(timeout)).authenticate("code")
        self.assertNotIn("sensitive", str(failure.exception))

    async def test_cancellation_is_not_converted_to_authentication_failure(self):
        async def cancel(request):
            raise asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.adapter(httpx.MockTransport(cancel)).authenticate("code")

    async def test_malformed_provider_response_is_denied(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, text="not-json"))
        with self.assertRaises(JiraLoginDenied):
            await self.adapter(transport).authenticate("code")


class JiraOAuthAuthTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = settings()
        self.tokens = JwtService(self.settings)
        self.oauth = Mock(spec=JiraOAuthPort)
        self.oauth.authorization_url.side_effect = lambda state, **kwargs: f"https://auth.atlassian.com/authorize?state={state}"
        self.identity = AuthIdentity("jira:cloud-123:account:123", "superadmin", "jira", profile_version=1)
        self.oauth.authenticate = AsyncMock(return_value=self.identity)
        self.profiles = Mock(spec=PersonalDataProfilePort)
        self.profiles.register_identity = AsyncMock(side_effect=lambda identity: replace(identity, profile_version=1))
        self.profiles.resolve_identity = AsyncMock(side_effect=lambda identity: replace(identity, display_name="superadmin"))
        self.reporting = Mock(spec=PersonalDataReportingPort)
        self.reporting.save_reporting_grant = AsyncMock()
        self.reporting.reporting_status = AsyncMock(return_value={"owner_authorized": False})
        self.reporting.run_reporting = AsyncMock(return_value={"status": "ok"})
        self.auth = AuthService(
            self.tokens, True, "admin", "admin-password", "superadmin", "superadmin-password", 7, False,
            jira_oauth=self.oauth, personal_data=self.profiles, reporting=self.reporting,
            privacy_owner_account_id="account:123",
        )
        self.audit = Mock()
        self.app = FastAPI()
        self.app.state.services = SimpleNamespace(auth=self.auth, audit=self.audit)
        self.app.include_router(router, prefix="/api/v1")

        @self.app.get("/ordinary")
        async def ordinary(username: str = Depends(require_auth)):
            return {"username": username}

        @self.app.get("/restricted")
        async def restricted(username: str = Depends(require_superadmin)):
            return {"username": username}

    def client(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def start(self, client):
        response = await client.post("/api/v1/auth/jira/start")
        self.assertEqual(200, response.status_code)
        return parse_qs(urlsplit(response.json()["authorization_url"]).query)["state"][0]

    async def callback(self, client, state, **params):
        return await client.get("/api/v1/auth/jira/callback", params={"state": state, "code": "code", **params})

    async def test_jira_success_refresh_and_me_preserve_identity_without_admin_privilege(self):
        async with self.client() as client:
            self.assertTrue((await client.get("/api/v1/auth/providers")).json()["jira"]["enabled"])
            state = await self.start(client)
            response = await self.callback(client, state)
            self.assertEqual(303, response.status_code)
            self.assertEqual("/login?jira=success", response.headers["location"])
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            self.assertNotIn(JIRA_STATE_COOKIE, client.cookies)
            me = (await client.get("/api/v1/auth/me")).json()
            self.assertEqual(self.identity.username, me["username"])
            self.assertEqual("superadmin", me["display_name"])
            self.assertEqual("jira", me["auth_provider"])
            self.assertFalse(me["is_superadmin"])
            refreshed = await client.post("/api/v1/auth/refresh")
            self.assertEqual(200, refreshed.status_code)
            token_data = refreshed.json()
            self.assertEqual("jira", token_data["auth_provider"])
            self.assertEqual("superadmin", token_data["display_name"])
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            self.assertEqual(200, (await client.get("/ordinary", headers=headers)).status_code)
            self.assertEqual(403, (await client.get("/restricted", headers=headers)).status_code)
            self.assertEqual(200, (await client.post("/api/v1/auth/logout")).status_code)
            self.assertEqual(401, (await client.post("/api/v1/auth/refresh")).status_code)
        self.oauth.authenticate.assert_awaited_once_with("code")
        self.assertNotIn("authorization", str(self.audit.record.call_args_list))

    async def test_state_cookie_is_http_only_lax_and_expires_after_ten_minutes(self):
        self.auth.cookie_secure = True
        async with self.client() as client:
            response = await client.post("/api/v1/auth/jira/start")
            cookie = response.headers["set-cookie"]
            for expected in ("HttpOnly", "Secure", "SameSite=lax", "Max-Age=600", "Path=/api/v1/auth/jira"):
                self.assertIn(expected, cookie)
            self.assertEqual("no-store", response.headers["cache-control"])

    async def test_missing_mismatched_or_expired_state_never_exchanges_code(self):
        async with self.client() as client:
            response = await self.callback(client, "missing")
            self.assertEqual("/login?jira=denied", response.headers["location"])
            await self.start(client)
            response = await self.callback(client, "mismatch")
            self.assertEqual("/login?jira=denied", response.headers["location"])
            state = await self.start(client)
            self.auth._jira_states[state] = 0
            response = await self.callback(client, state)
            self.assertEqual("/login?jira=denied", response.headers["location"])
            self.assertNotIn("refresh_token", client.cookies)
        self.oauth.authenticate.assert_not_awaited()

    async def test_state_is_single_use_even_when_cookie_is_replayed(self):
        async with self.client() as client:
            state = await self.start(client)
            await self.callback(client, state)
            client.cookies.set(JIRA_STATE_COOKIE, state, path="/api/v1/auth/jira")
            response = await self.callback(client, state)
            self.assertEqual("/login?jira=denied", response.headers["location"])
        self.oauth.authenticate.assert_awaited_once()

    async def test_consent_denial_clears_state_and_does_not_call_provider(self):
        async with self.client() as client:
            state = await self.start(client)
            response = await self.callback(client, state, error="access_denied", error_description="private information")
            self.assertEqual("/login?jira=denied", response.headers["location"])
            self.assertNotIn(JIRA_STATE_COOKIE, client.cookies)
            self.assertNotIn("private information", str(response.headers))
            self.assertNotIn("private information", str(self.audit.record.call_args_list))
        self.oauth.authenticate.assert_not_awaited()

    async def test_cross_site_cookie_mutation_requests_are_rejected(self):
        async with self.client() as client:
            for endpoint in ("jira/start", "refresh", "logout", "login"):
                response = await client.post(
                    f"/api/v1/auth/{endpoint}", headers={"Origin": "https://attacker.test"},
                    json={"username": "admin", "password": "admin-password"},
                )
                self.assertEqual(403, response.status_code)
            response = await client.post("/api/v1/auth/jira/start", headers={"Sec-Fetch-Site": "cross-site"})
            self.assertEqual(403, response.status_code)
            self.assertEqual(200, (await client.post("/api/v1/auth/jira/start", headers={"Origin": "http://test"})).status_code)

    async def test_unconfigured_jira_preserves_local_login_and_returns_unavailable(self):
        self.auth._jira_oauth = None
        async with self.client() as client:
            self.assertFalse((await client.get("/api/v1/auth/providers")).json()["jira"]["enabled"])
            self.assertEqual(503, (await client.post("/api/v1/auth/jira/start")).status_code)
            login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin-password"})
            self.assertEqual(200, login.status_code)
            self.assertEqual("local", login.json()["auth_provider"])
            self.assertEqual(200, (await client.post("/api/v1/auth/refresh")).status_code)

    async def test_provider_failure_redirects_without_provider_details(self):
        self.oauth.authenticate.side_effect = JiraLoginUnavailable("upstream-sensitive-message")
        async with self.client() as client:
            state = await self.start(client)
            response = await self.callback(client, state)
            self.assertEqual("/login?jira=unavailable", response.headers["location"])
            self.assertNotIn("upstream-sensitive-message", str(response.headers))
            self.assertNotIn("refresh_token", client.cookies)

    async def test_refresh_does_not_extend_jira_session_or_cookie_past_initial_deadline(self):
        deadline = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        identity = replace(self.identity, session_expires_at=deadline)
        async with self.client() as client:
            client.cookies.set("refresh_token", self.tokens.create_identity_refresh_token(identity), path="/api/v1/auth")
            response = await client.post("/api/v1/auth/refresh")
            self.assertEqual(200, response.status_code)
            access = self.tokens.decode_access_identity(response.json()["access_token"])
            self.assertEqual(deadline, access.session_expires_at)
            restored = self.tokens.decode_refresh_identity(response.cookies["refresh_token"])
            self.assertEqual(deadline, restored.session_expires_at)
            self.assertNotIn("Max-Age=604800", response.headers["set-cookie"])

    async def test_disabling_jira_invalidates_existing_jira_session(self):
        identity = replace(self.identity, session_expires_at=int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()))
        async with self.client() as client:
            client.cookies.set("refresh_token", self.tokens.create_identity_refresh_token(identity), path="/api/v1/auth")
            self.auth._jira_oauth = None
            self.assertEqual(401, (await client.post("/api/v1/auth/refresh")).status_code)
            self.assertEqual(401, (await client.get("/api/v1/auth/me")).status_code)

    async def test_namespaced_subject_cannot_collide_with_configured_local_admin(self):
        self.auth.admin_username = self.identity.username
        async with self.client() as client:
            state = await self.start(client)
            response = await self.callback(client, state)
            self.assertEqual("/login?jira=denied", response.headers["location"])
            self.assertNotIn("refresh_token", client.cookies)

    async def root_login(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "username": "superadmin", "password": "superadmin-password",
        })
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def test_owner_reporting_flow_keeps_root_session_and_stores_only_expected_owner_grant(self):
        self.oauth.authenticate_reporting_owner = AsyncMock(return_value=JiraReportingGrant(self.identity, "private-grant"))
        async with self.client() as client:
            headers = await self.root_login(client)
            old_cookie = client.cookies["refresh_token"]
            self.assertEqual(200, (await client.get("/api/v1/auth/jira/privacy/status", headers=headers)).status_code)
            started = await client.post("/api/v1/auth/jira/privacy/start", headers=headers)
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            self.oauth.authorization_url.assert_called_with(state, include_offline=True)
            completed = await self.callback(client, state)
            self.assertEqual("/admin/jira-privacy?jira_privacy=success", completed.headers["location"])
            self.assertEqual(old_cookie, client.cookies["refresh_token"])
            self.assertTrue((await client.get("/api/v1/auth/me")).json()["is_superadmin"])
        self.reporting.save_reporting_grant.assert_awaited_once_with("account:123", "private-grant")
        self.oauth.authenticate.assert_not_awaited()
        self.assertNotIn("private-grant", str(self.audit.record.call_args_list))

    async def test_owner_flow_rejects_other_atlassian_account(self):
        other = replace(self.identity, username="jira:cloud-123:other-account")
        self.oauth.authenticate_reporting_owner = AsyncMock(return_value=JiraReportingGrant(other, "private-grant"))
        async with self.client() as client:
            headers = await self.root_login(client)
            started = await client.post("/api/v1/auth/jira/privacy/start", headers=headers)
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            completed = await self.callback(client, state)
            self.assertEqual("/admin/jira-privacy?jira_privacy=denied", completed.headers["location"])
        self.reporting.save_reporting_grant.assert_not_awaited()

    async def test_owner_flow_cannot_finish_after_root_session_is_replaced(self):
        async with self.client() as client:
            headers = await self.root_login(client)
            started = await client.post("/api/v1/auth/jira/privacy/start", headers=headers)
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            await self.root_login(client)
            completed = await self.callback(client, state)
            self.assertEqual("/admin/jira-privacy?jira_privacy=denied", completed.headers["location"])
        self.oauth.authenticate_reporting_owner.assert_not_called()
        self.reporting.save_reporting_grant.assert_not_awaited()

    async def test_reporting_endpoints_require_root_and_same_origin(self):
        async with self.client() as client:
            for endpoint in ("status", "start", "run"):
                method = client.get if endpoint == "status" else client.post
                self.assertEqual(401, (await method(f"/api/v1/auth/jira/privacy/{endpoint}")).status_code)
            login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin-password"})
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            self.assertEqual(403, (await client.get("/api/v1/auth/jira/privacy/status", headers=headers)).status_code)
            headers = await self.root_login(client)
            for endpoint in ("start", "run"):
                response = await client.post(f"/api/v1/auth/jira/privacy/{endpoint}", headers={**headers, "Origin": "https://attacker.test"})
                self.assertEqual(403, response.status_code)
        self.reporting.save_reporting_grant.assert_not_awaited()

    async def test_owner_flow_rechecks_root_session_after_provider_response(self):
        async def exchange(code):
            self.auth.begin_superadmin_session()
            return JiraReportingGrant(self.identity, "private-grant")
        self.oauth.authenticate_reporting_owner = AsyncMock(side_effect=exchange)
        async with self.client() as client:
            headers = await self.root_login(client)
            started = await client.post("/api/v1/auth/jira/privacy/start", headers=headers)
            state = parse_qs(urlsplit(started.json()["authorization_url"]).query)["state"][0]
            completed = await self.callback(client, state)
            self.assertEqual("/admin/jira-privacy?jira_privacy=denied", completed.headers["location"])
        self.reporting.save_reporting_grant.assert_not_awaited()

    async def test_deleted_or_stale_profile_invalidates_access_and_refresh(self):
        async with self.client() as client:
            state = await self.start(client)
            await self.callback(client, state)
            data = (await client.post("/api/v1/auth/refresh")).json()
            self.profiles.resolve_identity.side_effect = ValueError("Profile revoked")
            headers = {"Authorization": f"Bearer {data['access_token']}"}
            self.assertEqual(401, (await client.get("/ordinary", headers=headers)).status_code)
            self.assertEqual(401, (await client.get("/api/v1/auth/me")).status_code)
            self.assertEqual(401, (await client.post("/api/v1/auth/refresh")).status_code)

    def test_state_cache_is_bounded_and_expired_entries_are_reclaimed(self):
        with patch("src.application.services.auth_service.monotonic", return_value=1):
            self.auth._jira_states = {str(index): 1000 for index in range(1024)}
            with self.assertRaises(JiraLoginUnavailable):
                self.auth.begin_jira_login()
        with patch("src.application.services.auth_service.monotonic", return_value=1001):
            state, _ = self.auth.begin_jira_login()
        self.assertEqual([state], list(self.auth._jira_states))


class JiraIdentityTokenTest(unittest.TestCase):
    def setUp(self):
        self.settings = settings()
        self.tokens = JwtService(self.settings)
        self.identity = AuthIdentity(
            "jira:cloud-123:account:123", "김영준", "jira",
            int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp()),
            1,
        )

    def test_identity_is_signed_and_round_trips_in_both_token_types(self):
        access = self.tokens.create_identity_access_token(self.identity)
        refresh = self.tokens.create_identity_refresh_token(self.identity)
        decoded_identity = replace(self.identity, display_name=self.identity.username)
        self.assertEqual(decoded_identity, self.tokens.decode_access_identity(access))
        self.assertEqual(decoded_identity, self.tokens.decode_refresh_identity(refresh))
        self.assertNotIn("display_name", jwt.decode(access, self.settings.jwt_secret, algorithms=["HS256"]))
        self.assertEqual(self.identity.username, self.tokens.decode_access_token(access))
        self.assertEqual(self.identity.username, self.tokens.decode_refresh_token(refresh))
        with self.assertRaises(ValueError):
            self.tokens.decode_access_identity(refresh)

    def test_expiration_is_required_and_expired_or_tampered_token_is_rejected(self):
        base = {"sub": self.identity.username, "type": "refresh", "auth_provider": "jira", "display_name": "김영준"}
        for payload, secret in (
            (base, self.settings.jwt_secret),
            ({**base, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, self.settings.jwt_secret),
            ({**base, "exp": datetime.now(timezone.utc) + timedelta(days=1)}, "wrong-key"),
            ({**base, "sub": "superadmin", "exp": datetime.now(timezone.utc) + timedelta(days=1)}, self.settings.jwt_secret),
        ):
            with self.subTest(payload=payload):
                token = jwt.encode(payload, secret, algorithm="HS256")
                with self.assertRaises(ValueError):
                    self.tokens.decode_refresh_identity(token)

    def test_legacy_local_token_remains_usable_with_safe_metadata_defaults(self):
        token = jwt.encode(
            {"sub": "admin", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
            self.settings.jwt_secret, algorithm="HS256",
        )
        self.assertEqual(AuthIdentity("admin", "admin", "local"), self.tokens.decode_access_identity(token))

    def test_jira_refresh_preserves_absolute_expiry_and_access_cannot_outlive_it(self):
        deadline = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        identity = replace(self.identity, session_expires_at=deadline)
        first = self.tokens.create_identity_refresh_token(identity)
        restored = self.tokens.decode_refresh_identity(first)
        second = self.tokens.create_identity_refresh_token(restored)
        access = self.tokens.create_identity_access_token(restored)
        for token in (first, second, access):
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
            self.assertEqual(deadline, payload["session_exp"])
            self.assertEqual(deadline, payload["exp"])

    def test_jira_tokens_require_absolute_expiry_and_cannot_extend_it(self):
        with self.assertRaises(ValueError):
            self.tokens.create_identity_refresh_token(replace(self.identity, session_expires_at=None))
        for extra in (
            {},
            {"session_exp": int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp())},
            {"session_exp": int((datetime.now(timezone.utc) + timedelta(minutes=1)).timestamp())},
        ):
            payload = {
                "sub": self.identity.username, "type": "refresh", "auth_provider": "jira",
                "display_name": self.identity.display_name,
                "exp": datetime.now(timezone.utc) + timedelta(days=1), **extra,
            }
            token = jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")
            with self.assertRaises(ValueError):
                self.tokens.decode_refresh_identity(token)
