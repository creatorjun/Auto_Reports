# backend/tests/test_gemini_client.py
import threading
import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.infrastructure.external.gemini_client import GeminiClient

_MODULE = "src.infrastructure.external.gemini_client"


class GeminiClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_close_releases_both_transports_once(self) -> None:
        client = Mock()
        client.aio.aclose = AsyncMock()
        with patch(f"{_MODULE}.genai.Client", return_value=client):
            adapter = GeminiClient("test-key")

        await adapter.aclose()
        await adapter.aclose()

        client.close.assert_called_once_with()
        client.aio.aclose.assert_awaited_once_with()
        client.models.generate_content.assert_not_called()

    async def test_disabled_client_close_does_not_create_sdk_resources(self) -> None:
        with patch(f"{_MODULE}.genai.Client") as create_client:
            adapter = GeminiClient("")
            await adapter.aclose()
            await adapter.aclose()

        create_client.assert_not_called()

    async def test_sync_close_runs_outside_event_loop_thread(self) -> None:
        loop_thread = threading.get_ident()
        close_threads: list[int] = []
        client = Mock()
        client.close.side_effect = lambda: close_threads.append(threading.get_ident())
        client.aio.aclose = AsyncMock()
        with patch(f"{_MODULE}.genai.Client", return_value=client):
            adapter = GeminiClient("test-key")

        await adapter.aclose()

        self.assertEqual(1, len(close_threads))
        self.assertNotEqual(loop_thread, close_threads[0])
        client.aio.aclose.assert_awaited_once_with()

    async def test_async_transport_closes_when_sync_cleanup_fails(self) -> None:
        client = Mock()
        client.close.side_effect = RuntimeError("sync cleanup failed")
        client.aio.aclose = AsyncMock()
        with patch(f"{_MODULE}.genai.Client", return_value=client):
            adapter = GeminiClient("test-key")

        with self.assertRaisesRegex(RuntimeError, "sync cleanup failed"):
            await adapter.aclose()
        await adapter.aclose()

        client.close.assert_called_once_with()
        client.aio.aclose.assert_awaited_once_with()
