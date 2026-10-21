# backend/tests/test_jira_user_grants.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI
from jose import jwt

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraOAuthPort
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.ports.personal_data_port import PersonalDataProfilePort
from src.application.services.auth_service import AuthService
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.jira_oauth_client import JiraOAuthClient
from src.infrastructure.security.jwt_service import JwtService
from src.infrastructure.security.memory_jira_user_grant_store import MemoryJiraUserGrantStore


def identity(**changes) -> AuthIdentity:
    return replace(AuthIdentity("jira:cloud-123:account:123", "사용자", "jira", profile_version=1), **changes)


def settings() -> Settings:
    return Settings(
        _env_file=None, jira_base_url="https://company.atlassian.net", jira_email="service@example.test",
        jira_api_token="service-token", LOGIN=True, ADMIN="admin", ADMIN_PASSWORD="password",
        JWT_SECRET="test-secret-only", jira_login_enabled=True,
    )


class MemoryJiraUserGrantStoreTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime.now(timezone.utc)
        self.clock = Mock(return_value=0.0)
        self.store = MemoryJiraUserGrantStore(max_entries=2, clock=self.clock, now=lambda: self.now)
        self.addAsyncCleanup(self.store.aclose)
        self.grant = JiraUserGrant("cloud-123", "account:123", "sensitive-access-token", self.now + timedelta(seconds=60))

    async def put(self, grant=None, owner=None):
        owner = owner or identity()
        grant_id = await self.store.put(grant or self.grant, owner)
        return replace(owner, jira_grant_id=grant_id)

    async def test_opaque_reference_is_bound_to_owner_provider_cloud_and_session(self):
        owner = await self.put()
        self.assertRegex(owner.jira_grant_id, r"^[A-Za-z0-9_-]{43}$")
        self.assertIs(self.grant, await self.store.get(owner.jira_grant_id, owner))
        for changed in (
            replace(owner, username="jira:cloud-123:other-account"),
            replace(owner, username="jira:other-cloud:account:123"),
            replace(owner, auth_provider="local"),
            replace(owner, jira_grant_id=None),
            replace(owner, jira_grant_id="x" * 43),
        ):
            with self.subTest(username=changed.username):
                self.assertIsNone(await self.store.get(owner.jira_grant_id, changed))
        self.assertNotIn(self.grant.access_token, repr(self.grant))
        self.assertNotIn(self.grant.access_token, repr(owner))

    async def test_revoke_cannot_revoke_another_owner_and_invalidates_in_flight_reference(self):
        owner = await self.put()
        reference = await self.store.get(owner.jira_grant_id, owner)
        await self.store.revoke(owner.jira_grant_id, replace(owner, username="jira:cloud-123:other"))
        self.assertIs(reference, await self.store.get(owner.jira_grant_id, owner))
        await self.store.revoke(owner.jira_grant_id, owner)
        self.assertIsNone(await self.store.get(owner.jira_grant_id, owner))
        await self.store.revoke(owner.jira_grant_id, owner)

    async def test_actual_expiry_is_enforced_without_extending_on_read(self):
        owner = await self.put()
        self.clock.return_value = 59.999
        self.assertIsNotNone(await self.store.get(owner.jira_grant_id, owner))
        self.clock.return_value = 60
        self.assertIsNone(await self.store.get(owner.jira_grant_id, owner))
        self.assertEqual(0, len(self.store._entries))

    async def test_capacity_evicts_oldest_after_pruning_and_never_grows_unbounded(self):
        first = await self.put()
        second = await self.put()
        third = await self.put()
        self.assertEqual(2, len(self.store._entries))
        self.assertIsNone(await self.store.get(first.jira_grant_id, first))
        self.assertIsNotNone(await self.store.get(second.jira_grant_id, second))
        self.assertIsNotNone(await self.store.get(third.jira_grant_id, third))
        self.clock.return_value = 60
        self.now += timedelta(seconds=60)
        latest = await self.put(replace(self.grant, expires_at=self.now + timedelta(seconds=60)))
        self.assertEqual(1, len(self.store._entries))
        self.assertIsNotNone(await self.store.get(latest.jira_grant_id, latest))

    async def test_expired_tokens_are_removed_even_without_later_requests(self):
        store = MemoryJiraUserGrantStore()
        self.addAsyncCleanup(store.aclose)
        grant = replace(self.grant, expires_at=datetime.now(timezone.utc) + timedelta(seconds=0.02))
        await store.put(grant, identity())
        await asyncio.sleep(0.06)
        self.assertEqual(0, len(store._entries))
        self.assertIsNone(store._expiry_timer)

    async def test_clear_revokes_all_and_allows_new_login_but_close_does_not(self):
        first = await self.put()
        await self.store.clear()
        self.assertIsNone(await self.store.get(first.jira_grant_id, first))
        second = await self.put()
        await self.store.aclose()
        await self.store.aclose()
        self.assertIsNone(await self.store.get(second.jira_grant_id, second))
        self.assertIsNone(self.store._expiry_timer)
        with self.assertRaises(ValueError):
            await self.put()

    async def test_invalid_and_expired_grants_are_not_retained(self):
        for grant in (
            replace(self.grant, expires_at=self.now),
            replace(self.grant, expires_at=self.now.replace(tzinfo=None)),
            replace(self.grant, account_id="other-account"),
            replace(self.grant, access_token=""),
            replace(self.grant, access_token="header\r\ninjection"),
        ):
            with self.subTest(expires=grant.expires_at), self.assertRaises(ValueError):
                await self.store.put(grant, identity())
        self.assertEqual(0, len(self.store._entries))

    def test_capacity_cannot_exceed_global_bound(self):
        for capacity in (0, -1, 1025, True):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                MemoryJiraUserGrantStore(max_entries=capacity)


class JiraOAuthUserGrantTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = MemoryJiraUserGrantStore()
        self.addAsyncCleanup(self.store.aclose)
        self.store.put = AsyncMock(wraps=self.store.put)
        self.token = {"access_token": "user-access-secret", "expires_in": 3600, "refresh_token": "owner-refresh-secret"}
        self.allowed = True
        self.adapter = JiraOAuthClient(
            "client", "client-secret", "http://test/api/v1/auth/jira/callback",
            "https://company.atlassian.net", "TACEA", grants=self.store,
            transport=httpx.MockTransport(self.respond),
        )

    def respond(self, request):
        path = request.url.path
        if path == "/oauth/token":
            return httpx.Response(200, json=self.token)
        if path.endswith("/accessible-resources"):
            return httpx.Response(200, json=[{
                "id": "cloud-123", "url": "https://company.atlassian.net",
                "scopes": ["read:jira-user", "read:jira-work"],
            }])
        if path.endswith("/myself"):
            return httpx.Response(200, json={
                "accountId": "account:123", "displayName": "사용자", "active": True, "accountType": "atlassian",
            })
        if path.endswith("/mypermissions"):
            return httpx.Response(200, json={"permissions": {"BROWSE_PROJECTS": {"havePermission": self.allowed}}})
        raise AssertionError(path)

    async def test_verified_login_preserves_user_token_and_provider_expiry_only_in_server_store(self):
        before = datetime.now(timezone.utc)
        result = await self.adapter.authenticate("code")
        after = datetime.now(timezone.utc)
        grant = await self.store.get(result.jira_grant_id, result)
        self.assertEqual(("cloud-123", "account:123", "user-access-secret"), (grant.cloud_id, grant.account_id, grant.access_token))
        self.assertGreaterEqual(grant.expires_at, before + timedelta(seconds=3600))
        self.assertLessEqual(grant.expires_at, after + timedelta(seconds=3600))
        self.assertNotIn("secret", repr(result))
        self.assertNotIn("owner-refresh-secret", repr(self.store._entries))
        scope = parse_qs(urlsplit(self.adapter.authorization_url("state")).query)["scope"]
        self.assertEqual(["read:jira-user read:jira-work"], scope)

    async def test_denied_project_permission_never_stores_a_grant(self):
        self.allowed = False
        with self.assertRaises(JiraLoginDenied):
            await self.adapter.authenticate("code")
        self.store.put.assert_not_awaited()

    async def test_missing_or_invalid_expiration_never_guesses_token_lifetime(self):
        for expires in (None, False, 0, -1, "3600", 1.5, 10 ** 100):
            with self.subTest(expires=expires):
                self.token["expires_in"] = expires
                with self.assertRaises(JiraLoginDenied):
                    await self.adapter.authenticate("code")
        self.store.put.assert_not_awaited()

    async def test_owner_reporting_flow_keeps_refresh_token_separate_and_never_stores_user_grant(self):
        self.token.pop("expires_in")
        result = await self.adapter.authenticate_reporting_owner("owner-code")
        self.assertEqual("owner-refresh-secret", result.refresh_token)
        self.assertIsNone(result.identity.jira_grant_id)
        self.store.put.assert_not_awaited()


class JiraGrantAuthAndJwtTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = MemoryJiraUserGrantStore()
        self.addAsyncCleanup(self.store.aclose)
        self.settings = settings()
        self.tokens = JwtService(self.settings)
        self.oauth = Mock(spec=JiraOAuthPort)
        self.profiles = Mock(spec=PersonalDataProfilePort)
        self.profiles.register_identity = AsyncMock(side_effect=lambda value: replace(value, profile_version=1))
        self.profiles.resolve_identity = AsyncMock(side_effect=lambda value: replace(value, display_name="사용자"))
        self.grant = JiraUserGrant("cloud-123", "account:123", "raw-user-secret", datetime.now(timezone.utc) + timedelta(hours=1))
        grant_id = await self.store.put(self.grant, identity())
        self.identity = replace(identity(), jira_grant_id=grant_id)
        self.oauth.authenticate = AsyncMock(return_value=self.identity)
        self.auth = AuthService(
            self.tokens, True, "admin", "password", "root", "root-password", 7, False,
            jira_oauth=self.oauth, personal_data=self.profiles, jira_grants=self.store,
        )

    async def test_access_and_refresh_jwt_preserve_only_opaque_reference_and_app_session(self):
        result = await self.auth.authenticate_jira("code")
        self.assertEqual(self.identity.jira_grant_id, result.jira_grant_id)
        access = self.tokens.create_identity_access_token(result)
        refresh = self.tokens.create_identity_refresh_token(result)
        for encoded in (access, refresh):
            payload = jwt.decode(encoded, self.settings.jwt_secret, algorithms=["HS256"])
            self.assertEqual(result.jira_grant_id, payload["jira_grant_id"])
            self.assertNotIn("raw-user-secret", str(payload))
            self.assertNotIn("access_token", payload)
            self.assertNotIn("refresh_token", payload)
        self.assertEqual(result.jira_grant_id, self.tokens.decode_access_identity(access).jira_grant_id)
        restored = await self.auth.resolve_refresh_identity(refresh)
        self.assertEqual(result.jira_grant_id, restored.jira_grant_id)
        self.assertEqual(result.session_expires_at, restored.session_expires_at)
        await self.store.revoke(result.jira_grant_id, result)
        self.assertEqual(result.username, (await self.auth.resolve_access_identity(access)).username)
        self.assertIsNone(await self.store.get(result.jira_grant_id, result))

    async def test_profile_registration_failure_or_cancellation_removes_grant(self):
        for failure in (ValueError("closed profile"), RuntimeError("database failed"), asyncio.CancelledError()):
            with self.subTest(failure=type(failure).__name__):
                grant_id = await self.store.put(self.grant, identity())
                current = replace(self.identity, jira_grant_id=grant_id)
                self.oauth.authenticate.return_value = current
                self.profiles.register_identity.side_effect = failure
                with self.assertRaises(type(failure)):
                    await self.auth.authenticate_jira("code")
                self.assertIsNone(await self.store.get(grant_id, current))

    async def test_logout_api_revokes_only_current_jira_grant_without_exposing_it(self):
        from src.presentation.api.v1.auth import router

        current = await self.auth.authenticate_jira("code")
        another_id = await self.store.put(self.grant, identity())
        another = replace(current, jira_grant_id=another_id)
        app = FastAPI()
        app.state.services = SimpleNamespace(auth=self.auth, audit=Mock())
        app.include_router(router, prefix="/api/v1")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            client.cookies.set("refresh_token", self.tokens.create_identity_refresh_token(current), path="/api/v1/auth")
            response = await client.post("/api/v1/auth/logout")
        self.assertEqual(200, response.status_code)
        self.assertNotIn(current.jira_grant_id, response.text)
        self.assertIsNone(await self.store.get(current.jira_grant_id, current))
        self.assertIsNotNone(await self.store.get(another_id, another))

    async def test_privacy_clear_invalidates_grants_without_changing_app_identity(self):
        result = await self.auth.authenticate_jira("code")
        access = self.tokens.create_identity_access_token(result)
        await self.auth.clear_jira_grants()
        self.assertIsNone(await self.store.get(result.jira_grant_id, result))
        self.assertEqual(result.username, (await self.auth.resolve_access_identity(access)).username)

    async def test_existing_jira_session_without_grant_still_authenticates(self):
        self.oauth.authenticate.return_value = replace(self.identity, jira_grant_id=None)
        result = await self.auth.authenticate_jira("code")
        encoded = self.tokens.create_identity_access_token(result)
        self.assertIsNone((await self.auth.resolve_access_identity(encoded)).jira_grant_id)

    async def test_local_or_malformed_opaque_references_are_rejected_in_jwt(self):
        current = await self.auth.authenticate_jira("code")
        for value in ("", "short", "raw token with spaces", 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.tokens.create_identity_access_token(replace(current, jira_grant_id=value))
        with self.assertRaises(ValueError):
            self.tokens.create_identity_access_token(AuthIdentity("admin", "admin", jira_grant_id=current.jira_grant_id))
        payload = jwt.decode(self.tokens.create_identity_access_token(current), self.settings.jwt_secret, algorithms=["HS256"])
        for changes in ({"jira_grant_id": "invalid"}, {"auth_provider": "local"}):
            encoded = jwt.encode(payload | changes, self.settings.jwt_secret, algorithm="HS256")
            with self.assertRaises(ValueError):
                self.tokens.decode_access_identity(encoded)
