# backend/tests/test_jira_oauth_persistent.py
import asyncio
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock

import httpx

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraPersistentGrant
from src.application.ports.jira_user_grant_port import JiraUserGrant, JiraUserGrantStorePort
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.external.jira_oauth_client import JiraOAuthClient


class JiraPersistentOAuthTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.token = {
            "access_token": "rotated-access-secret",
            "refresh_token": "rotated-refresh-secret",
            "expires_in": 3600,
        }
        self.resources = [{
            "id": "cloud-123", "url": "https://company.atlassian.net",
            "scopes": ["read:jira-user", "read:jira-work"],
        }]
        self.profile = {
            "accountId": "account:123", "displayName": "직원", "emailAddress": "engineer@company.example",
            "active": True, "accountType": "atlassian",
        }
        self.permissions = {"permissions": {"BROWSE_PROJECTS": {"havePermission": True}}}
        self.status = {}
        self.memory_store = Mock(spec=JiraUserGrantStorePort)
        self.grant = JiraUserGrant(
            "cloud-123", "account:123", "stored-access-secret",
            datetime.now(timezone.utc) + timedelta(minutes=5), "stored-refresh-secret",
        )

    def respond(self, request):
        self.requests.append(request)
        path = request.url.path
        if path in self.status:
            return httpx.Response(self.status[path], json={"error": "invalid_grant", "error_description": "provider-secret"})
        if path == "/oauth/token":
            return httpx.Response(200, json=self.token)
        if path.endswith("/accessible-resources"):
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
            transport=transport or httpx.MockTransport(self.respond), grants=self.memory_store,
        )

    def test_offline_scope_is_explicit_and_official_consent_parameter_is_preserved(self):
        adapter = self.adapter()
        for offline in (False, True):
            with self.subTest(offline=offline):
                query = parse_qs(urlsplit(adapter.authorization_url("state", include_offline=offline)).query)
                self.assertEqual(offline, "offline_access" in query["scope"][0].split())
                self.assertEqual(["consent"], query["prompt"])

    async def test_persistent_exchange_returns_verified_grant_without_memory_storage(self):
        before = datetime.now(timezone.utc)
        result = await self.adapter().authenticate_persistent("authorization-code")
        after = datetime.now(timezone.utc)
        self.assertIsInstance(result, JiraPersistentGrant)
        self.assertEqual(AuthIdentity(
            "jira:cloud-123:account:123", "직원", "jira", email_address="engineer@company.example",
        ), result.identity)
        self.assertIsNone(result.identity.jira_grant_id)
        self.assertEqual(("cloud-123", "account:123"), (result.grant.cloud_id, result.grant.account_id))
        self.assertEqual("rotated-access-secret", result.grant.access_token)
        self.assertEqual("rotated-refresh-secret", result.grant.refresh_token)
        self.assertLessEqual(before + timedelta(hours=1), result.grant.expires_at)
        self.assertGreaterEqual(after + timedelta(hours=1), result.grant.expires_at)
        self.assertNotIn("secret", repr(result))
        self.assertEqual(4, len(self.requests))
        self.assertEqual("authorization_code", json.loads(self.requests[0].content)["grant_type"])
        self.memory_store.put.assert_not_awaited()

    async def test_persistent_and_refresh_exchange_require_complete_valid_credentials(self):
        original = self.token.copy()
        cases = [
            (name, value)
            for name in ("access_token", "refresh_token")
            for value in (None, "", True, 123, "with space", "secret\r\nvalue", "secret\x00", "비밀", "x" * 32769)
        ]
        cases.extend(("expires_in", value) for value in (None, True, 0, -1, "3600", 1.5, 10 ** 100))
        for field, value in cases:
            self.token = {**original, field: value}
            for method in ("persistent", "refresh"):
                with self.subTest(field=field, value_type=type(value).__name__, method=method):
                    with self.assertRaises(JiraLoginDenied) as failure:
                        if method == "persistent":
                            await self.adapter().authenticate_persistent("sensitive-code")
                        else:
                            await self.adapter().refresh_user_grant(self.grant)
                    self.assertNotIn("secret", str(failure.exception))
                    self.assertNotIn("sensitive-code", str(failure.exception))
        self.memory_store.put.assert_not_awaited()

    async def test_refresh_only_rotates_tokens_without_running_identity_validation(self):
        self.profile["active"] = False
        expired = replace(self.grant, expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        before = datetime.now(timezone.utc)
        result = await self.adapter().refresh_user_grant(expired)
        after = datetime.now(timezone.utc)
        self.assertEqual(1, len(self.requests))
        request = self.requests[0]
        self.assertEqual("https://auth.atlassian.com/oauth/token", str(request.url))
        self.assertEqual({
            "grant_type": "refresh_token", "client_id": "client-id", "client_secret": "client-secret",
            "refresh_token": "stored-refresh-secret",
        }, json.loads(request.content))
        self.assertNotIn("authorization", request.headers)
        self.assertEqual(("cloud-123", "account:123"), (result.cloud_id, result.account_id))
        self.assertEqual("rotated-access-secret", result.access_token)
        self.assertEqual("rotated-refresh-secret", result.refresh_token)
        self.assertLessEqual(before + timedelta(hours=1), result.expires_at)
        self.assertGreaterEqual(after + timedelta(hours=1), result.expires_at)
        self.assertNotIn("secret", repr(result))
        self.assertEqual("stored-refresh-secret", expired.refresh_token)
        self.memory_store.put.assert_not_awaited()

    async def test_rotated_grant_is_returned_before_later_identity_validation_can_fail(self):
        adapter = self.adapter()
        rotated = await adapter.refresh_user_grant(self.grant)
        self.profile["active"] = False
        with self.assertRaises(JiraLoginDenied):
            await adapter.validate_user_grant(rotated)
        self.assertEqual("rotated-refresh-secret", rotated.refresh_token)
        self.assertEqual(3, len(self.requests))
        self.assertEqual("Bearer rotated-access-secret", self.requests[-1].headers["authorization"])

    async def test_refresh_refusal_and_transient_failures_have_distinct_safe_errors(self):
        for code in (400, 401, 403, 404, 429, 500, 503):
            with self.subTest(code=code):
                self.requests.clear()
                self.status["/oauth/token"] = code
                expected = JiraLoginUnavailable if code == 429 or code >= 500 else JiraLoginDenied
                with self.assertRaises(expected) as failure:
                    await self.adapter().refresh_user_grant(self.grant)
                self.assertEqual(1, len(self.requests))
                self.assertNotIn("secret", str(failure.exception))
                self.assertNotIn("invalid_grant", str(failure.exception))

    async def test_refresh_never_reuses_old_token_when_rotation_response_omits_new_refresh_token(self):
        del self.token["refresh_token"]
        with self.assertRaises(JiraLoginDenied):
            await self.adapter().refresh_user_grant(self.grant)
        self.assertEqual(1, len(self.requests))

    async def test_refresh_without_saved_offline_grant_is_denied_before_network(self):
        for value in (None, "", "injected\nheader"):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(JiraLoginDenied):
                await self.adapter().refresh_user_grant(replace(self.grant, refresh_token=value))
        self.assertEqual([], self.requests)

    async def test_validate_rechecks_current_site_profile_and_project_without_changing_grant(self):
        identity = await self.adapter().validate_user_grant(self.grant)
        self.assertEqual("jira:cloud-123:account:123", identity.username)
        self.assertEqual("engineer@company.example", identity.email_address)
        self.assertIsNone(identity.jira_grant_id)
        self.assertEqual(3, len(self.requests))
        for request in self.requests:
            self.assertEqual("GET", request.method)
            self.assertEqual("api.atlassian.com", request.url.host)
            self.assertEqual("Bearer stored-access-secret", request.headers["authorization"])
            self.assertNotIn("secret", str(request.url))
        self.assertEqual("TACEA", self.requests[-1].url.params["projectKey"])
        self.assertEqual("BROWSE_PROJECTS", self.requests[-1].url.params["permissions"])
        self.memory_store.put.assert_not_awaited()

    async def test_validate_rejects_changed_cloud_or_account_before_further_identity_requests(self):
        for grant, requests in (
            (replace(self.grant, cloud_id="other-cloud"), 1),
            (replace(self.grant, account_id="other-account"), 2),
        ):
            with self.subTest(cloud=grant.cloud_id, account=grant.account_id):
                self.requests.clear()
                with self.assertRaises(JiraLoginDenied):
                    await self.adapter().validate_user_grant(grant)
                self.assertEqual(requests, len(self.requests))

    async def test_validate_rejects_lost_site_scope_active_account_and_project_permission(self):
        original_resources = self.resources
        original_profile = self.profile
        original_permissions = self.permissions
        cases = (
            ([], original_profile, original_permissions),
            ([{**self.resources[0], "scopes": ["read:jira-user"]}], original_profile, original_permissions),
            ([{**self.resources[0], "url": "https://other.atlassian.net"}], original_profile, original_permissions),
            (original_resources, {**original_profile, "active": False}, original_permissions),
            (original_resources, {**original_profile, "accountType": "customer"}, original_permissions),
            (original_resources, original_profile, {"permissions": {"BROWSE_PROJECTS": {"havePermission": False}}}),
        )
        for resources, profile, permissions in cases:
            self.resources, self.profile, self.permissions = resources, profile, permissions
            with self.subTest(resources=bool(resources), active=profile["active"]), self.assertRaises(JiraLoginDenied):
                await self.adapter().validate_user_grant(self.grant)

    async def test_validate_requires_unexpired_timezone_aware_access_token(self):
        for grant in (
            replace(self.grant, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
            replace(self.grant, expires_at=datetime.now()),
            replace(self.grant, expires_at=None),
            replace(self.grant, access_token="header\nvalue"),
        ):
            with self.subTest(grant=grant), self.assertRaises(JiraLoginDenied):
                await self.adapter().validate_user_grant(grant)
        self.assertEqual([], self.requests)

    async def test_malformed_owner_is_rejected_before_refresh_or_validation(self):
        for grant in (replace(self.grant, cloud_id="../other"), replace(self.grant, account_id="../account")):
            for method in (self.adapter().refresh_user_grant, self.adapter().validate_user_grant):
                with self.subTest(grant=grant, method=method.__name__), self.assertRaises(JiraLoginDenied):
                    await method(grant)
        self.assertEqual([], self.requests)

    async def test_network_errors_are_unavailable_and_cancellation_propagates(self):
        def timeout(request):
            raise httpx.ReadTimeout("sensitive-upstream-details", request=request)

        async def cancelled(request):
            raise asyncio.CancelledError()

        for name in ("authenticate_persistent", "refresh_user_grant", "validate_user_grant"):
            argument = "sensitive-code" if name == "authenticate_persistent" else self.grant
            with self.subTest(method=name):
                with self.assertRaises(JiraLoginUnavailable) as failure:
                    await getattr(self.adapter(httpx.MockTransport(timeout)), name)(argument)
                self.assertNotIn("sensitive", str(failure.exception))
                with self.assertRaises(asyncio.CancelledError):
                    await getattr(self.adapter(httpx.MockTransport(cancelled)), name)(argument)

    async def test_malformed_refresh_response_is_denied_without_exposing_payload(self):
        for content in ("provider-secret", "null", "[]", "{}"):
            transport = httpx.MockTransport(lambda request: httpx.Response(200, text=content))
            with self.subTest(content_type=content[:1]), self.assertRaises(JiraLoginDenied) as failure:
                await self.adapter(transport).refresh_user_grant(self.grant)
            self.assertNotIn("provider-secret", str(failure.exception))
