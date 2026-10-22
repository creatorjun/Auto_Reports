# backend/tests/test_gemini_news_translator.py
import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pydantic import ValidationError

from src.application.ports.security_news_translation_port import NewsTranslationProviderError
from src.domain.entities.security_news_translation import NewsTranslationInput
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.gemini_news_translator import GeminiNewsTranslator


class GeminiNewsTranslatorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = Mock()
        self.client.aio.models.generate_content = AsyncMock()
        self.client.aio.aclose = AsyncMock()
        with patch("src.infrastructure.external.gemini_news_translator.genai.Client", return_value=self.client) as create:
            self.translator = GeminiNewsTranslator("private-test-key")
            self.options = create.call_args.kwargs["http_options"]
        self.input = NewsTranslationInput("id", "Original", "Summary")

    async def asyncTearDown(self) -> None:
        await self.translator.aclose()

    async def test_async_json_summary_has_one_http_attempt_and_no_tools_or_translated_title(self) -> None:
        self.client.aio.models.generate_content.return_value = SimpleNamespace(text=json.dumps({
            "translations": [{"id": "id", "summary_ko": "보안 업데이트가 제공되었습니다."}],
        }))
        result = await self.translator.translate((self.input,))
        self.assertEqual("", result[0].title_ko)
        self.assertEqual("보안 업데이트가 제공되었습니다.", result[0].summary_ko)
        self.assertEqual(1, self.options.retry_options.attempts)
        arguments = self.client.aio.models.generate_content.call_args.kwargs
        self.assertEqual("gemini-3.5-flash-lite", arguments["model"])
        self.assertIsNone(arguments["config"].tools)
        self.assertTrue(arguments["config"].automatic_function_calling.disable)
        self.assertEqual(8192, arguments["config"].max_output_tokens)
        schema = arguments["config"].response_json_schema["properties"]["translations"]["items"]
        self.assertEqual(["id", "summary_ko"], schema["required"])
        self.assertNotIn("title_ko", schema["properties"])
        self.assertIn("180 characters", arguments["config"].system_instruction)
        self.assertIn("one concise Korean sentence", arguments["config"].system_instruction)
        self.assertEqual([{"id": "id", "title": "Original", "summary": "Summary"}], json.loads(arguments["contents"]))
        self.assertNotIn("private-test-key", arguments["contents"])
        self.client.models.generate_content.assert_not_called()

    async def test_explicit_free_tier_model_is_used_without_substitution(self) -> None:
        with patch("src.infrastructure.external.gemini_news_translator.genai.Client", return_value=self.client):
            translator = GeminiNewsTranslator("private-test-key", "gemini-3.1-flash-lite")
        self.client.aio.models.generate_content.return_value = SimpleNamespace(text='{"translations":[]}')
        try:
            await translator.translate((self.input,))
            self.assertEqual("gemini-3.1-flash-lite", self.client.aio.models.generate_content.call_args.kwargs["model"])
            self.client.aio.models.generate_content.assert_awaited_once()
        finally:
            await translator.aclose()

    async def test_rejected_models_never_create_a_client(self) -> None:
        for model in (
            "gemini-3.1-pro-preview", "gemini-4-argon", "unknown-model", "gemini-flash-lite-latest",
            "gemini-3.1-flash-lite-preview", "models/gemini-3.5-flash-lite",
            " gemini-3.5-flash-lite", "gemini-3.5-flash-lite/", "GEMINI-3.5-FLASH-LITE", "",
        ):
            with self.subTest(model=model), patch("src.infrastructure.external.gemini_news_translator.genai.Client") as create:
                with self.assertRaises(ValueError):
                    GeminiNewsTranslator("private-test-key", model)
                create.assert_not_called()

    async def test_duplicates_unknown_ids_and_invalid_peers_do_not_discard_valid_results(self) -> None:
        self.client.aio.models.generate_content.return_value = SimpleNamespace(text=json.dumps({
            "translations": [
                {"id": "id", "summary_ko": "요약"},
                {"id": "id", "summary_ko": "충돌"},
                {"id": "other", "summary_ko": "정상"},
                {"id": "foreign", "summary_ko": "모르는 항목"},
                {"id": "broken", "summary_ko": []},
                {"id": "broken", "summary_ko": "중복"},
                {"id": "legacy", "title_ko": "이전 제목 번역", "summary_ko": "이전 전체 번역"},
            ],
        }))
        result = await self.translator.translate((
            self.input, NewsTranslationInput("other", "Title", ""),
            NewsTranslationInput("broken", "Duplicate", ""),
            NewsTranslationInput("legacy", "Old title", "Old excerpt"),
        ))
        self.assertEqual(["other"], [value.key for value in result])

    async def test_http_failures_are_typed_without_leaking_raw_provider_message(self) -> None:
        for code, reason in ((400, "authorization"), (402, "billing"), (401, "authorization"), (403, "authorization"), (404, "authorization"), (429, "quota"), (500, "provider")):
            error = RuntimeError("secret raw body")
            error.code = code
            self.client.aio.models.generate_content.reset_mock()
            self.client.aio.models.generate_content.side_effect = error
            with self.assertRaises(NewsTranslationProviderError) as caught:
                await self.translator.translate((self.input,))
            self.assertEqual(reason, caught.exception.reason)
            self.assertNotIn("secret", str(caught.exception))
            self.client.aio.models.generate_content.assert_awaited_once()
            self.assertEqual("gemini-3.5-flash-lite", self.client.aio.models.generate_content.call_args.kwargs["model"])

    async def test_invalid_json_is_a_bounded_content_failure(self) -> None:
        for body in ("not json", '{"translations":42}', "[]"):
            self.client.aio.models.generate_content.return_value = SimpleNamespace(text=body)
            with self.assertRaises(NewsTranslationProviderError) as caught:
                await self.translator.translate((self.input,))
            self.assertEqual("invalid", caught.exception.reason)

    async def test_cancellation_propagates_without_retry(self) -> None:
        self.client.aio.models.generate_content.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.translator.translate((self.input,))
        self.client.aio.models.generate_content.assert_awaited_once()

    async def test_close_releases_both_transports_once(self) -> None:
        await self.translator.aclose()
        await self.translator.aclose()
        self.client.aio.aclose.assert_awaited_once()
        self.client.close.assert_called_once()


class GeminiNewsTranslationSettingsTest(unittest.TestCase):
    def settings(self, **values) -> Settings:
        return Settings(
            _env_file=None, jira_base_url="https://jira.example.test", jira_email="test@example.test",
            jira_api_token="test", **values,
        )

    def test_settings_default_matches_the_free_tier_translator(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("gemini-3.5-flash-lite", self.settings().security_news_translation_model)

    def test_environment_accepts_only_exact_supported_free_tier_ids(self) -> None:
        for model in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
            with self.subTest(model=model), patch.dict(os.environ, {"SECURITY_NEWS_TRANSLATION_MODEL": model}, clear=True):
                self.assertEqual(model, self.settings().security_news_translation_model)
        for model in (
            "gemini-4-argon", "gemini-3.1-pro-preview", "unknown", "gemini-flash-lite-latest",
            "models/gemini-3.5-flash-lite", "gemini-3.1-flash-lite-preview", "gemini-3.5-flash-lite ", "",
        ):
            with self.subTest(model=model), patch.dict(os.environ, {"SECURITY_NEWS_TRANSLATION_MODEL": model}, clear=True):
                with self.assertRaises(ValidationError):
                    self.settings()
