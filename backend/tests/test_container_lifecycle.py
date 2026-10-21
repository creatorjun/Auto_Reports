# backend/tests/test_container_lifecycle.py
import asyncio
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.application.ports.ai_port import AiPort
from src.application.ports.jira_port import JiraPort
from src.application.ports.email_port import EmailPort
from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.application.ports.sla_violation_port import SlaViolationSourcePort
from src.application.ports.sla_digest_port import SlaDigestSourcePort, SlaDigestRendererPort
from src.application.ports.sla_status_snapshot_port import SlaStatusSnapshotPort
from src.bootstrap.container import Container
from src.infrastructure.config.settings import Settings
from src.domain.entities.security_news import SecurityNewsItem
from src.domain.entities.security_news_translation import NewsTranslationInput, NewsTranslationReservation
from src.application.services.security_news_translation import translation_key


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
        self.sla_source = AsyncMock(spec=SlaViolationSourcePort)
        self.redeployment_source = AsyncMock()
        self.digest_source = AsyncMock(spec=SlaDigestSourcePort)
        self.digest_source.fetch_entries.return_value = ()
        self.sla_snapshots = AsyncMock(spec=SlaStatusSnapshotPort)
        self.sla_snapshots.load.return_value = None
        self.sla_snapshots.save.side_effect = lambda project_key, snapshot: snapshot

    def create_container(self, ai: AiPort | None) -> Container:
        with (
            patch("src.bootstrap.container.JiraFactory.create", return_value=self.jira),
            patch("src.bootstrap.container.AiFactory.create", return_value=ai),
            patch("src.bootstrap.container.SlaViolationJiraSource", return_value=self.sla_source),
            patch("src.bootstrap.container.RedeploymentJiraSource", return_value=self.redeployment_source),
            patch("src.bootstrap.container.SlaDigestJiraSource", return_value=self.digest_source),
            patch("src.bootstrap.container.SlaStatusSnapshotRepository", return_value=self.sla_snapshots),
        ):
            return Container(self.settings, Mock())

    async def test_shutdown_closes_owned_ai_and_jira(self) -> None:
        container = self.create_container(self.ai)
        news_source_close = AsyncMock(wraps=container._security_news_source.aclose)
        container._security_news_source.aclose = news_source_close

        await container.aclose()

        self.ai.aclose.assert_awaited_once_with()
        self.jira.aclose.assert_awaited_once_with()
        self.sla_source.aclose.assert_awaited_once_with()
        self.redeployment_source.aclose.assert_awaited_once_with()
        news_source_close.assert_awaited_once_with()
        self.assertTrue(container._jira_notification_source._client.is_closed)
        self.assertTrue(container._jira_user_grants._closed)
        self.assertTrue(container.security_news._closed)
        self.assertTrue(container._security_news_source._client.is_closed)
        self.assertIsNone(container._news_translation)
        self.digest_source.aclose.assert_awaited_once_with()

    async def test_sla_status_is_available_without_email_and_never_sends_notifications(self) -> None:
        container = self.create_container(None)
        try:
            self.assertFalse(container.sla_digest_enabled)
            result = await container.sla_status.get_snapshot()
            self.assertEqual(0, result.ticket_count)
            self.digest_source.fetch_entries.assert_awaited_once_with()
            self.sla_snapshots.load.assert_awaited_once_with(self.settings.project_key)
            self.sla_snapshots.save.assert_awaited_once_with(self.settings.project_key, result)
            self.assertIsNone(container._notify_todo)
        finally:
            await container.aclose()
        self.digest_source.aclose.assert_awaited_once_with()

    async def test_sla_status_stops_before_shared_source_and_invalidates_personal_data(self) -> None:
        container = self.create_container(None)
        container.issue_management.clear_personal_data_cache = AsyncMock()
        self.jira.clear_personal_data_cache = AsyncMock()
        container.sla_status.clear_personal_data_cache = AsyncMock()
        container.auth.clear_jira_grants = AsyncMock()
        try:
            await container._clear_personal_data_caches()
            container.sla_status.clear_personal_data_cache.assert_awaited_once_with()
            container.auth.clear_jira_grants.assert_awaited_once_with()
            events = []
            container.sla_status.aclose = AsyncMock(side_effect=lambda: events.append("status"))
            self.digest_source.aclose.side_effect = lambda: events.append("source")
        finally:
            await container.aclose()
        self.assertEqual(["status", "source"], events)

    async def test_news_translation_is_independent_of_report_ai_and_closes_worker_before_dependencies(self) -> None:
        self.settings.ai_enabled = False
        self.settings.gemini_api_key = "fixture-key"
        translator = AsyncMock()
        cache = AsyncMock()
        cache.read.return_value = {}
        item = SecurityNewsItem("one", "nvd", "cve", "Security issue", "A product vulnerability", "https://example.com")
        request = NewsTranslationInput(translation_key(item.title, item.summary), item.title, item.summary)
        cache.reserve.return_value = NewsTranslationReservation((request,))
        entered = asyncio.Event()
        events = []

        async def translate(inputs):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                events.append("worker")

        translator.translate.side_effect = translate
        translator.aclose.side_effect = lambda: events.append("translator")
        cache.aclose.side_effect = lambda: events.append("cache")
        with (
            patch("src.bootstrap.container.GeminiNewsTranslator", return_value=translator),
            patch("src.bootstrap.container.SqliteNewsTranslationCache", return_value=cache),
        ):
            container = self.create_container(None)
        self.assertIsNotNone(container._news_translation)
        container._news_translation.snapshot((item,))
        await entered.wait()
        await container.aclose()
        self.assertEqual(["worker", "cache", "translator"], events)

    async def test_enabled_notifications_receive_the_renderer_from_bootstrap(self) -> None:
        self.settings.smtp_host = "smtp.example.test"
        self.settings.notify_todo_enabled = True
        self.settings.notify_todo_to = ["test@example.test"]
        self.settings.notify_tac_enabled = True
        self.settings.notify_tac_to = ["test@example.test"]
        email = AsyncMock(spec=EmailPort)
        with patch("src.bootstrap.container.Container._build_smtp", return_value=email):
            container = self.create_container(None)
        try:
            self.assertIsNotNone(container._notify_todo)
            self.assertIsNotNone(container._notify_tac)
            self.assertIsInstance(container._notify_todo._renderer, IssueNotificationRendererPort)
            self.assertIs(container._notify_todo._renderer, container._notify_tac._renderer)
            self.assertTrue(container.sla_digest_enabled)
            self.assertIsInstance(container._notify_sla_digest._renderer, SlaDigestRendererPort)
            self.assertEqual(self.settings.notify_todo_to, container._notify_sla_digest._notify_to)
            self.assertIs(container._notify_todo._email, container._notify_sla_digest._email)
            self.assertEqual(0, await container.send_sla_digest())
            self.digest_source.fetch_entries.assert_awaited_once_with()
            await container._notify_todo.execute([])
            await container._notify_tac.execute({})
            email.send.assert_not_awaited()
        finally:
            await container.aclose()
        self.digest_source.aclose.assert_awaited_once_with()

    async def test_digest_is_disabled_without_existing_todo_notification(self) -> None:
        for smtp, enabled, recipients in (
            (None, True, ["test@example.test"]),
            (AsyncMock(spec=EmailPort), False, ["test@example.test"]),
            (AsyncMock(spec=EmailPort), True, []),
        ):
            with self.subTest(smtp=bool(smtp), enabled=enabled, recipients=bool(recipients)):
                self.settings.notify_todo_enabled = enabled
                self.settings.notify_todo_to = recipients
                with patch("src.bootstrap.container.Container._build_smtp", return_value=smtp):
                    container = self.create_container(None)
                try:
                    self.assertFalse(container.sla_digest_enabled)
                    self.assertIsNone(container._sla_digest_source)
                    self.assertEqual(0, await container.send_sla_digest())
                finally:
                    await container.aclose()
        self.digest_source.fetch_entries.assert_not_awaited()

    async def test_digest_can_be_disabled_without_disabling_todo(self) -> None:
        self.settings.notify_todo_enabled = True
        self.settings.notify_todo_to = ["test@example.test"]
        self.settings.notify_sla_digest_enabled = False
        with patch("src.bootstrap.container.Container._build_smtp", return_value=AsyncMock(spec=EmailPort)):
            container = self.create_container(None)
        try:
            self.assertIsNotNone(container._notify_todo)
            self.assertFalse(container.sla_digest_enabled)
            self.assertIsNone(container._sla_digest_source)
        finally:
            await container.aclose()

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
        self.sla_source.aclose.assert_awaited_once_with()
