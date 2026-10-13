# backend/tests/test_superadmin_auth.py
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from fastapi import Depends, FastAPI, Request
from jose import jwt

from src.application.services.auth_service import AuthService
from src.infrastructure.config.settings import Settings
from src.infrastructure.security.jwt_service import JwtService
from src.presentation.api.v1.auth import router as auth_router
from src.presentation.api.v1.deps import require_auth, require_superadmin
from src.presentation.http.request_audit import RequestAudit


class SuperadminAuthTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings(
            _env_file=None, jira_base_url="https://jira.example.test", jira_email="test@example.test",
            jira_api_token="test", LOGIN=True, ADMIN="admin", ADMIN_PASSWORD="ordinary-password",
            SUPERADMIN="root", SUPERADMIN_PASSWORD="administrator-password", JWT_SECRET="test-secret-only",
        )
        self.tokens = JwtService(self.settings)
        self.auth = AuthService(self.tokens, True, "admin", "ordinary-password", "root", "administrator-password", 7, False)
        self.audit = Mock()
        self.app = FastAPI()
        self.app.state.services = SimpleNamespace(auth=self.auth, audit=self.audit)
        self.app.include_router(auth_router, prefix="/api/v1")

        @self.app.get("/restricted")
        async def restricted(username: str = Depends(require_superadmin)):
            return {"username": username}

        @self.app.get("/ordinary")
        async def ordinary(username: str = Depends(require_auth)):
            return {"username": username}

    def client(self):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def login(self, client, username="root", password="administrator-password"):
        response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
        self.assertEqual(200, response.status_code)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def test_superadmin_role_and_read_access_use_server_configuration(self):
        async with self.client() as client:
            headers = await self.login(client)
            response = await client.get("/api/v1/auth/me")
            self.assertTrue(response.json()["is_superadmin"])
            self.assertEqual(200, (await client.get("/restricted", headers=headers)).status_code)
            self.assertEqual(200, (await client.get("/ordinary", headers=headers)).status_code)
        self.audit.record.assert_called_with("LOGIN_SUCCESS", ip="127.0.0.1", username="root")

    async def test_ordinary_admin_stays_ordinary_and_cannot_view_audit(self):
        async with self.client() as client:
            headers = await self.login(client, "admin", "ordinary-password")
            self.assertFalse((await client.get("/api/v1/auth/me")).json()["is_superadmin"])
            self.assertEqual(403, (await client.get("/restricted", headers=headers)).status_code)
            self.assertEqual(200, (await client.get("/ordinary", headers=headers)).status_code)

    async def test_missing_forged_query_and_refresh_tokens_are_rejected(self):
        async with self.client() as client:
            headers = await self.login(client)
            access = headers["Authorization"].split()[1]
            self.assertEqual(401, (await client.get("/restricted")).status_code)
            self.assertEqual(401, (await client.get("/restricted", params={"token": access})).status_code)
            forged = jwt.encode({"sub": "root", "type": "access", "gen": 1}, "wrong-secret", algorithm="HS256")
            missing_session = self.tokens.create_access_token("root")
            refresh = self.tokens.create_refresh_token("root", 1)
            for token in (forged, missing_session, refresh):
                self.assertEqual(401, (await client.get("/restricted", headers={"Authorization": f"Bearer {token}"})).status_code)

    async def test_previous_superadmin_session_is_invalidated_and_new_one_refreshes(self):
        async with self.client() as client:
            old = await self.login(client)
            current = await self.login(client)
            self.assertEqual(401, (await client.get("/restricted", headers=old)).status_code)
            self.assertEqual(200, (await client.get("/restricted", headers=current)).status_code)
            response = await client.post("/api/v1/auth/refresh")
            self.assertEqual(200, response.status_code)
            self.assertEqual(200, (await client.get("/restricted", headers={"Authorization": f"Bearer {response.json()['access_token']}"})).status_code)

    async def test_disabled_login_never_opens_audit_logs(self):
        self.auth.enabled = False
        async with self.client() as client:
            self.assertEqual(403, (await client.get("/restricted")).status_code)
            self.assertFalse((await client.get("/api/v1/auth/me")).json()["is_superadmin"])
            self.assertEqual(200, (await client.get("/ordinary")).status_code)

    async def test_login_failure_and_logout_are_audited_without_passwords(self):
        async with self.client() as client:
            failure = await client.post("/api/v1/auth/login", json={"username": "사용자", "password": "비밀"})
            self.assertEqual(401, failure.status_code)
            self.audit.record.assert_called_with("LOGIN_FAILED", ip="127.0.0.1", username="사용자")
            await self.login(client)
            self.assertEqual(200, (await client.post("/api/v1/auth/logout")).status_code)
            self.audit.record.assert_called_with("LOGOUT", ip="127.0.0.1", username="root")
            self.assertEqual(401, (await client.get("/api/v1/auth/me")).status_code)

    def test_ambiguous_or_unconfigured_superadmin_is_not_administrator(self):
        self.auth.superadmin_username = "admin"
        self.assertFalse(self.auth.is_superadmin_user("admin"))
        self.auth.superadmin_username = ""
        self.assertFalse(self.auth.is_superadmin_user(""))

    async def test_identical_account_names_preserve_ordinary_login_without_elevation(self):
        self.settings.superadmin_username = "admin"
        self.auth.superadmin_username = "admin"
        async with self.client() as client:
            headers = await self.login(client, "admin", "ordinary-password")
            self.assertEqual(200, (await client.get("/ordinary", headers=headers)).status_code)
            self.assertEqual(403, (await client.get("/restricted", headers=headers)).status_code)
            me = await client.get("/api/v1/auth/me")
            self.assertEqual(200, me.status_code)
            self.assertFalse(me.json()["is_superadmin"])
            refreshed = await client.post("/api/v1/auth/refresh")
            self.assertEqual(200, refreshed.status_code)
            refreshed_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
            self.assertEqual(200, (await client.get("/ordinary", headers=refreshed_headers)).status_code)
            self.assertEqual(403, (await client.get("/restricted", headers=refreshed_headers)).status_code)
            elevated_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "administrator-password"})
            self.assertEqual(401, elevated_login.status_code)

    def test_configured_account_name_is_not_hardcoded_to_root(self):
        self.auth.superadmin_username = "operator"
        self.assertTrue(self.auth.is_superadmin_user("operator"))
        self.assertFalse(self.auth.is_superadmin_user("root"))

    def test_request_audit_adds_verified_actor_and_cannot_be_overridden(self):
        request = Request({"type": "http", "headers": []})
        request.state.authenticated_username = "admin"
        RequestAudit(self.audit, request).record("FILE_UPLOAD", username="root", path="file.txt")
        self.audit.record.assert_called_with("FILE_UPLOAD", username="admin", path="file.txt")
