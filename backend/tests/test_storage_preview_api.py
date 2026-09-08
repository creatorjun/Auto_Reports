# backend/tests/test_storage_preview_api.py
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.auth_service import AuthService
from src.application.use_cases.storage_use_case import StorageUseCase
from src.presentation.api.deps import get_auth, get_storage_use_case
from src.presentation.api.v1.storage import preview_router


class StoragePreviewApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = pathlib.Path(self.directory.name) / "보고 자료.pptx"
        self.source.write_bytes(b"presentation-content")
        self.auth = Mock(spec=AuthService)
        self.auth.enabled = True
        self.auth.decode_access_token.side_effect = self.decode_token
        self.use_case = Mock(spec=StorageUseCase)
        self.use_case.get_file_path = AsyncMock(return_value=str(self.source))
        self.use_case.get_mime_type.return_value = "application/octet-stream"
        self.use_case.is_convertible.return_value = True
        self.use_case.convert_to_pdf = AsyncMock(return_value=b"%PDF-1.4 preview")
        app = FastAPI()
        app.include_router(preview_router, prefix="/api/v1")
        app.dependency_overrides[get_auth] = lambda: self.auth
        app.dependency_overrides[get_storage_use_case] = lambda: self.use_case
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)

    @staticmethod
    def decode_token(token: str) -> str:
        if token != "valid-token":
            raise ValueError("Invalid or expired token")
        return "preview-user"

    async def test_accepts_bearer_header_on_all_preview_routes(self) -> None:
        for route in ("preview", "preview-converted", "download"):
            with self.subTest(route=route):
                response = await self.client.get(
                    f"/api/v1/storage/{route}",
                    params={"folder": "자료", "name": self.source.name},
                    headers={"Authorization": "Bearer valid-token"},
                )
                self.assertEqual(200, response.status_code)
                expected = b"%PDF-1.4 preview" if route == "preview-converted" else b"presentation-content"
                self.assertEqual(expected, response.content)
        self.use_case.convert_to_pdf.assert_awaited_once_with("자료", self.source.name)

    async def test_preserves_query_token_links(self) -> None:
        for route in ("preview", "preview-converted", "download"):
            with self.subTest(route=route):
                response = await self.client.get(
                    f"/api/v1/storage/{route}",
                    params={"name": self.source.name, "_t": "valid-token"},
                )
                self.assertEqual(200, response.status_code)

    async def test_rejects_missing_invalid_and_non_bearer_credentials(self) -> None:
        for route in ("preview", "preview-converted", "download"):
            for headers, query in (
                ({}, {}),
                ({"Authorization": "Bearer expired-token"}, {}),
                ({"Authorization": "Basic valid-token"}, {}),
                ({"Authorization": "Bearer "}, {}),
                ({}, {"_t": "expired-token"}),
                ({"Authorization": "Bearer expired-token"}, {"_t": "valid-token"}),
            ):
                with self.subTest(route=route, headers=headers, query=query):
                    response = await self.client.get(
                        f"/api/v1/storage/{route}",
                        params={"name": self.source.name, **query},
                        headers=headers,
                    )
                    self.assertEqual(401, response.status_code)
        self.use_case.get_file_path.assert_not_awaited()
        self.use_case.convert_to_pdf.assert_not_awaited()

    async def test_accepts_case_insensitive_bearer_scheme(self) -> None:
        response = await self.client.get(
            "/api/v1/storage/preview-converted",
            params={"name": self.source.name},
            headers={"Authorization": "bearer valid-token"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/pdf", response.headers["content-type"])

    async def test_preserves_access_when_login_is_disabled(self) -> None:
        self.auth.enabled = False
        response = await self.client.get(
            "/api/v1/storage/preview-converted", params={"name": self.source.name},
        )
        self.assertEqual(200, response.status_code)
        self.auth.decode_access_token.assert_not_called()

    async def test_preserves_conversion_error_status_and_detail(self) -> None:
        for exception, status, detail in (
            (FileNotFoundError(), 404, "File not found"),
            (TimeoutError(), 504, "Conversion timed out"),
            (RuntimeError("PDF conversion failed"), 500, "PDF conversion failed"),
        ):
            with self.subTest(status=status):
                self.use_case.convert_to_pdf.side_effect = exception
                response = await self.client.get(
                    "/api/v1/storage/preview-converted",
                    params={"name": self.source.name},
                    headers={"Authorization": "Bearer valid-token"},
                )
                self.assertEqual(status, response.status_code)
                self.assertEqual(detail, response.json()["detail"])
