# backend/tests/test_auth_proxy_headers.py
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from fastapi import FastAPI
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.application.services.auth_service import AuthService
from src.infrastructure.config.settings import Settings
from src.infrastructure.security.jwt_service import JwtService
from src.presentation.api.v1.auth import router


class AuthProxyHeadersTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        settings = Settings(
            _env_file=None, jira_base_url="https://jira.example.test", jira_email="user@example.test",
            jira_api_token="test", LOGIN=True, ADMIN="admin", ADMIN_PASSWORD="password",
            JWT_SECRET="test-only-secret", COOKIE_SECURE=True,
        )
        app = FastAPI()
        app.state.services = SimpleNamespace(
            auth=AuthService(JwtService(settings), True, "admin", "password", "", "", 7, True),
            audit=Mock(),
        )
        app.include_router(router, prefix="/api/v1")
        self.app = ProxyHeadersMiddleware(app, trusted_hosts="172.19.0.0/16")

    async def login(self, proxy_ip, origin):
        transport = httpx.ASGITransport(app=self.app, client=(proxy_ip, 12345))
        async with httpx.AsyncClient(transport=transport, base_url="http://server.test") as client:
            return await client.post(
                "/api/v1/auth/login", json={"username": "admin", "password": "password"},
                headers={"Origin": origin, "X-Forwarded-Proto": "https"},
            )

    async def test_trusted_proxy_cidr_restores_https_origin_and_secure_cookie(self):
        response = await self.login("172.19.0.3", "https://server.test")
        self.assertEqual(200, response.status_code)
        self.assertIn("Secure", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    async def test_untrusted_client_cannot_spoof_https_forwarding(self):
        response = await self.login("198.51.100.8", "https://server.test")
        self.assertEqual(403, response.status_code)

    async def test_trusted_proxy_does_not_bypass_origin_validation(self):
        response = await self.login("172.19.0.3", "https://attacker.test")
        self.assertEqual(403, response.status_code)
