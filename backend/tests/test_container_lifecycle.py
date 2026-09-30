# backend/tests/test_container_lifecycle.py
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.application.ports.ai_port import AiPort
from src.application.ports.jira_port import JiraPort
from src.bootstrap.container import Container
from src.infrastructure.config.settings import Settings


class ContainerLifecycleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.settings = Settings.model_construct(
            jira_base_url="https://jira.example.test",
            jira_email="user",
            jira_api_token="test-token",
            storage_dir=workspace.name,
        )
        self.jira = Mock(spec=JiraPort)
        self.ai = Mock(spec=AiPort)

    def create_container(self, ai: AiPort | None) -> Container:
        with (
            patch("src.bootstrap.container.JiraFactory.create", return_value=self.jira),
            patch("src.bootstrap.container.AiFactory.create", return_value=ai),
        ):
            return Container(self.settings, Mock())

    async def test_shutdown_closes_owned_ai_and_jira(self) -> None:
        container = self.create_container(self.ai)

        await container.aclose()

        self.ai.aclose.assert_awaited_once_with()
        self.jira.aclose.assert_awaited_once_with()

    async def test_shutdown_without_ai_still_closes_jira(self) -> None:
        self.settings.ai_enabled = False
        container = self.create_container(None)

        await container.aclose()

        self.jira.aclose.assert_awaited_once_with()

    async def test_ai_close_failure_does_not_skip_jira_cleanup(self) -> None:
        container = self.create_container(self.ai)
        self.ai.aclose.side_effect = RuntimeError("AI close failed")

        with self.assertRaisesRegex(RuntimeError, "AI close failed"):
            await container.aclose()

        self.ai.aclose.assert_awaited_once_with()
        self.jira.aclose.assert_awaited_once_with()

    async def test_earlier_close_failure_does_not_skip_ai_cleanup(self) -> None:
        container = self.create_container(self.ai)
        container.issue_management.aclose = AsyncMock(
            side_effect=RuntimeError("Issue close failed"),
        )
        cache_close = AsyncMock(wraps=container._cache.aclose)
        container._cache.aclose = cache_close

        with self.assertRaisesRegex(RuntimeError, "Issue close failed"):
            await container.aclose()

        cache_close.assert_awaited_once_with()
        self.ai.aclose.assert_awaited_once_with()
        self.jira.aclose.assert_awaited_once_with()
