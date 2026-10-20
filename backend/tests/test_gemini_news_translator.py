# backend/tests/test_gemini_news_translator.py
import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.application.ports.security_news_translation_port import NewsTranslationProviderError
from src.domain.entities.security_news_translation import NewsTranslationInput
from src.infrastructure.external.gemini_news_translator import GeminiNewsTranslator


class GeminiNewsTranslatorTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = Mock()
        self.client.aio.models.generate_content = AsyncMock()
        self.client.aio.aclose = AsyncMock()
        with patch("src.infrastructure.external.gemini_news_translator.genai.Client", return_value=self.client) as create:
            self.translator = GeminiNewsTranslator("private-test-key", "test-model")
            self.options = create.call_args.kwargs["http_options"]
        self.input = NewsTranslationInput("id", "Original", "Summary")

    async def asyncTearDown(self) -> None:
        await self.translator.aclose()

    async def test_async_json_translation_has_one_http_attempt_and_no_tools(self) -> None:
        self.client.aio.models.generate_content.return_value = SimpleNamespace(text=json.dumps({
            "translations": [{"id": "id", "title_ko": "제목", "summary_ko": "요약"}],
        }))
        result = await self.translator.translate((self.input,))
        self.assertEqual("제목", result[0].title_ko)
        self.assertEqual(1, self.options.retry_options.attempts)
        arguments = self.client.aio.models.generate_content.call_args.kwargs
        self.assertEqual("test-model", arguments["model"])
        self.assertIsNone(arguments["config"].tools)
        self.assertTrue(arguments["config"].automatic_function_calling.disable)
        self.assertEqual(16384, arguments["config"].max_output_tokens)
        self.assertNotIn("private-test-key", arguments["contents"])
        self.client.models.generate_content.assert_not_called()

    async def test_duplicates_unknown_ids_and_invalid_peers_do_not_discard_valid_results(self) -> None:
        self.client.aio.models.generate_content.return_value = SimpleNamespace(text=json.dumps({
            "translations": [
                {"id": "id", "title_ko": "제목", "summary_ko": "요약"},
                {"id": "id", "title_ko": "충돌", "summary_ko": "요약"},
                {"id": "other", "title_ko": "정상", "summary_ko": ""},
                {"id": "foreign", "title_ko": "모르는 항목", "summary_ko": ""},
                {"id": "broken", "title_ko": 10, "summary_ko": []},
                {"id": "broken", "title_ko": "중복", "summary_ko": ""},
            ],
        }))
        result = await self.translator.translate((
            self.input, NewsTranslationInput("other", "Title", ""),
            NewsTranslationInput("broken", "Duplicate", ""),
        ))
        self.assertEqual(["other"], [value.key for value in result])

    async def test_http_failures_are_typed_without_leaking_raw_provider_message(self) -> None:
        for code, reason in ((400, "authorization"), (402, "billing"), (401, "authorization"), (403, "authorization"), (404, "authorization"), (429, "quota"), (500, "provider")):
            error = RuntimeError("secret raw body")
            error.code = code
            self.client.aio.models.generate_content.side_effect = error
            with self.assertRaises(NewsTranslationProviderError) as caught:
                await self.translator.translate((self.input,))
            self.assertEqual(reason, caught.exception.reason)
            self.assertNotIn("secret", str(caught.exception))

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
