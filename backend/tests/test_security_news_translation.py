# backend/tests/test_security_news_translation.py
import asyncio
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from src.application.ports.security_news_translation_port import NewsTranslationProviderError
from src.application.services.security_news_translation import (
    SecurityNewsTranslationService,
    needs_translation,
    translation_key,
    valid_translation,
)
from src.domain.entities.security_news import SecurityNewsItem
from src.domain.entities.security_news_translation import NewsTranslation, NewsTranslationInput
from src.infrastructure.persistence.security_news_translation_cache import SqliteNewsTranslationCache


class SecurityNewsTranslationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "translations.sqlite3")
        self.now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        self.services = []
        self.caches = []
        self.item = SecurityNewsItem(
            "first", "nvd", "cve", "CVE-2026-1234 critical security issue",
            "Product 1.2 contains a vulnerability.", "https://example.com/",
        )

    async def asyncTearDown(self) -> None:
        for service in self.services:
            await service.aclose()
        for cache in self.caches:
            await cache.aclose()
        self.directory.cleanup()

    def service(self, **kwargs):
        provider = AsyncMock()
        provider.translate.side_effect = lambda inputs: tuple(
            NewsTranslation(value.key, value.title + " 한국어", value.summary + " 한국어" if value.summary else "")
            for value in inputs
        )
        cache = SqliteNewsTranslationCache(self.path)
        service = SecurityNewsTranslationService(
            provider, cache, clock=lambda: self.now, minimum_interval_seconds=0, **kwargs,
        )
        self.services.append(service)
        self.caches.append(cache)
        return service, provider, cache

    async def finish(self, service, items):
        initial = service.snapshot(tuple(items))
        if service._task is not None:
            await service._task
        return initial, service.snapshot(tuple(items))

    def scalar(self, query):
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute(query).fetchone()[0]

    async def test_original_is_immediate_then_persisted_translation_is_exposed(self) -> None:
        service, provider, _ = self.service()
        gate = asyncio.Event()
        started = asyncio.Event()

        async def translate(inputs):
            started.set()
            await gate.wait()
            return tuple(NewsTranslation(value.key, value.title + " 한국어", value.summary + " 한국어") for value in inputs)

        provider.translate.side_effect = translate
        items, state = service.snapshot((self.item,))
        self.assertIsNone(items[0].title_ko)
        self.assertTrue(state.translating)
        await started.wait()
        self.assertIsNone(service.snapshot((self.item,))[0][0].title_ko)
        gate.set()
        await service._task
        items, state = service.snapshot((self.item,))
        self.assertEqual(self.item.title, items[0].title)
        self.assertTrue(items[0].title_ko.endswith("한국어"))
        self.assertEqual(1, state.translated_count)
        self.assertEqual(0, state.pending_count)
        self.assertEqual(1, self.scalar("SELECT COUNT(*) FROM translations"))

    async def test_identical_content_deduplicates_sources_refreshes_and_restarts(self) -> None:
        service, provider, _ = self.service()
        duplicate = replace(self.item, id="another", source_id="cisa-kev")
        _, (_, state) = await self.finish(service, (self.item, duplicate))
        self.assertEqual(2, state.translated_count)
        self.assertEqual(1, len(provider.translate.await_args.args[0]))
        for _ in range(20):
            service.snapshot((self.item, duplicate))
        self.assertEqual(1, provider.translate.await_count)
        await service.aclose()
        restarted, new_provider, _ = self.service()
        _, (items, state) = await self.finish(restarted, (duplicate, self.item))
        new_provider.translate.assert_not_awaited()
        self.assertEqual(2, state.translated_count)
        self.assertEqual(items[0].title_ko, items[1].title_ko)

    async def test_only_changed_original_content_is_translated_again(self) -> None:
        service, provider, _ = self.service()
        await self.finish(service, (self.item,))
        changed_source = replace(self.item, id="changed-id", source_id="google-security")
        await self.finish(service, (changed_source,))
        self.assertEqual(1, provider.translate.await_count)
        changed_content = replace(changed_source, summary="Product 1.3 contains a vulnerability.")
        await self.finish(service, (changed_content,))
        self.assertEqual(2, provider.translate.await_count)
        self.assertEqual(2, self.scalar("SELECT COUNT(*) FROM translations"))

    async def test_repeated_snapshots_share_one_worker(self) -> None:
        service, provider, _ = self.service()
        gate = asyncio.Event()
        original = provider.translate.side_effect

        async def translate(inputs):
            await gate.wait()
            return original(inputs)

        provider.translate.side_effect = translate
        for _ in range(30):
            service.snapshot((self.item,))
        gate.set()
        await service._task
        provider.translate.assert_awaited_once()

    async def test_partial_valid_results_are_saved_and_failed_peer_is_not_retried_immediately(self) -> None:
        service, provider, _ = self.service()
        second = replace(self.item, id="second", title="A different security issue")

        def translate(inputs):
            return (
                NewsTranslation(inputs[0].key, inputs[0].title + " 한국어", inputs[0].summary + " 한국어"),
                NewsTranslation(inputs[1].key, "", "잘못된 응답"),
            )

        provider.translate.side_effect = translate
        _, (items, state) = await self.finish(service, (self.item, second))
        self.assertIsNotNone(items[0].title_ko)
        self.assertIsNone(items[1].title_ko)
        self.assertEqual(1, state.pending_count)
        self.assertEqual(1, provider.translate.await_count)
        self.assertEqual(1, self.scalar("SELECT COUNT(*) FROM translations"))
        restarted, other, _ = self.service()
        await self.finish(restarted, (self.item, second))
        other.translate.assert_not_awaited()

    async def test_daily_request_budget_survives_restart_and_resets_on_next_utc_day(self) -> None:
        service, provider, _ = self.service(daily_limit=1, batch_size=1)
        second = replace(self.item, id="second", title="Another security issue")
        _, (_, state) = await self.finish(service, (self.item, second))
        self.assertEqual(1, provider.translate.await_count)
        self.assertIn("오늘", state.message)
        restarted, other, _ = self.service(daily_limit=1, batch_size=1)
        await self.finish(restarted, (self.item, second))
        other.translate.assert_not_awaited()
        self.now += timedelta(days=1)
        await self.finish(restarted, (self.item, second))
        other.translate.assert_awaited_once()
        self.assertEqual(2, self.scalar("SELECT SUM(used) FROM request_budget"))

    async def test_zero_daily_budget_never_calls_provider(self) -> None:
        service, provider, _ = self.service(daily_limit=0)
        _, (_, state) = await self.finish(service, (self.item,))
        provider.translate.assert_not_awaited()
        self.assertIn("한도", state.message)
        self.assertEqual(0, self.scalar("SELECT COUNT(*) FROM request_budget"))

    async def test_quota_cooldown_is_persistent_and_exponential(self) -> None:
        service, provider, _ = self.service()
        provider.translate.side_effect = NewsTranslationProviderError("quota")
        await self.finish(service, (self.item,))
        self.assertEqual(self.now.timestamp() + 3600, self.scalar("SELECT next_request_at FROM translation_control"))
        restarted, other, _ = self.service()
        other.translate.side_effect = NewsTranslationProviderError("quota")
        await self.finish(restarted, (self.item,))
        other.translate.assert_not_awaited()
        self.now += timedelta(hours=1)
        await self.finish(restarted, (self.item,))
        other.translate.assert_awaited_once()
        self.assertEqual(self.now.timestamp() + 7200, self.scalar("SELECT next_request_at FROM translation_control"))
        self.assertEqual(0, self.scalar("SELECT attempt_count FROM attempts"))

    async def test_billing_failure_pauses_twenty_four_hours_even_after_source_change(self) -> None:
        service, provider, _ = self.service()
        provider.translate.side_effect = NewsTranslationProviderError("billing")
        _, (_, state) = await self.finish(service, (self.item,))
        self.assertIn("크레딧", state.message)
        self.assertEqual(self.now.timestamp() + 86400, self.scalar("SELECT next_request_at FROM translation_control"))
        changed = replace(self.item, id="new", title="Another security issue")
        restarted, other, _ = self.service()
        await self.finish(restarted, (changed,))
        other.translate.assert_not_awaited()
        self.assertEqual(1, self.scalar("SELECT SUM(used) FROM request_budget"))

    async def test_content_failures_are_bounded_and_not_reset_by_restart(self) -> None:
        for attempt in range(3):
            service, provider, _ = self.service()
            provider.translate.side_effect = NewsTranslationProviderError("invalid")
            await self.finish(service, (self.item,))
            provider.translate.assert_awaited_once()
            self.now += timedelta(days=1)
        service, provider, _ = self.service()
        await self.finish(service, (self.item,))
        provider.translate.assert_not_awaited()
        self.assertEqual(3, self.scalar("SELECT attempt_count FROM attempts"))
        for _ in range(10):
            self.assertFalse(service.snapshot((self.item,))[1].translating)

    async def test_provider_outage_pauses_other_batches_for_five_minutes(self) -> None:
        service, provider, _ = self.service(batch_size=1)
        provider.translate.side_effect = NewsTranslationProviderError("provider")
        second = replace(self.item, id="second", title="Another security issue")
        await self.finish(service, (self.item, second))
        provider.translate.assert_awaited_once()
        self.assertEqual(self.now.timestamp() + 300, self.scalar("SELECT next_request_at FROM translation_control"))

    async def test_new_content_arriving_during_exhausted_reservation_is_not_suppressed(self) -> None:
        service, provider, cache = self.service(max_attempts=1)
        first = NewsTranslationInput(translation_key(self.item.title, self.item.summary), self.item.title, self.item.summary)
        await cache.reserve((first,), now=self.now, daily_limit=60, batch_size=10, minimum_interval_seconds=0, max_attempts=1)
        entered, release = asyncio.Event(), asyncio.Event()
        reserve = cache.reserve
        calls = 0

        async def paused_reserve(inputs, **kwargs):
            nonlocal calls
            calls += 1
            result = await reserve(inputs, **kwargs)
            if calls == 1:
                entered.set()
                await release.wait()
            return result

        cache.reserve = paused_reserve
        service.snapshot((self.item,))
        await entered.wait()
        second = replace(self.item, id="second", title="Another security issue")
        service.snapshot((self.item, second))
        release.set()
        await service._task
        provider.translate.assert_awaited_once()
        self.assertEqual("Another security issue", provider.translate.await_args.args[0][0].title)
        self.assertEqual(1, service.snapshot((self.item, second))[1].translated_count)

    async def test_new_content_arriving_during_cache_read_reloads_persistent_translation(self) -> None:
        service, provider, cache = self.service()
        second = replace(self.item, id="second", title="Another security issue")
        request = NewsTranslationInput(translation_key(second.title, second.summary), second.title, second.summary)
        await cache.complete((request,), (NewsTranslation(request.key, request.title + " 한국어", request.summary + " 한국어"),), now=self.now)
        entered, release = asyncio.Event(), asyncio.Event()
        read = cache.read
        calls = 0

        async def paused_read(keys):
            nonlocal calls
            calls += 1
            result = await read(keys)
            if calls == 1:
                entered.set()
                await release.wait()
            return result

        cache.read = paused_read
        service.snapshot((self.item,))
        await entered.wait()
        service.snapshot((second,))
        release.set()
        await service._task
        provider.translate.assert_not_awaited()
        self.assertIsNotNone(service.snapshot((second,))[0][0].title_ko)

    async def test_cache_failure_stops_translation_without_leaking_exception_text(self) -> None:
        provider, cache = AsyncMock(), AsyncMock()
        cache.read.side_effect = PermissionError("private-key-and-path")
        service = SecurityNewsTranslationService(provider, cache)
        self.services.append(service)
        _, (items, state) = await self.finish(service, (self.item,))
        self.assertIn("저장소", state.message)
        self.assertNotIn("private", state.message)
        self.assertIsNone(items[0].title_ko)
        for _ in range(5):
            service.snapshot((self.item,))
        cache.read.assert_awaited_once()
        provider.translate.assert_not_awaited()

    async def test_cache_write_failure_does_not_expose_unsaved_translation(self) -> None:
        service, provider, cache = self.service()
        cache.complete = AsyncMock(side_effect=OSError("secret-path"))
        _, (items, state) = await self.finish(service, (self.item,))
        self.assertIsNone(items[0].title_ko)
        self.assertIn("저장소", state.message)
        service.snapshot((self.item,))
        self.assertEqual(1, provider.translate.await_count)

    async def test_shutdown_cancels_provider_before_returning(self) -> None:
        service, provider, _ = self.service()
        entered = asyncio.Event()
        cancelled = asyncio.Event()

        async def translate(inputs):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        provider.translate.side_effect = translate
        service.snapshot((self.item,))
        await entered.wait()
        await service.aclose()
        self.assertTrue(cancelled.is_set())
        self.assertEqual(1, self.scalar("SELECT SUM(used) FROM request_budget"))

    async def test_korean_items_skip_provider_and_empty_summaries_remain_empty(self) -> None:
        service, provider, _ = self.service()
        korean = replace(self.item, source_id="kisa", title="보안 업데이트 권고", summary="")
        items, state = service.snapshot((korean,))
        self.assertFalse(state.translating)
        self.assertEqual(0, state.pending_count)
        provider.translate.assert_not_awaited()
        title_only = replace(self.item, summary="")
        _, (items, _) = await self.finish(service, (title_only,))
        self.assertEqual("", items[0].summary_ko)


class TranslationValidationTest(unittest.TestCase):
    def test_content_hash_does_not_use_source_model_or_prompt_versions(self) -> None:
        self.assertEqual(translation_key("title", "summary"), translation_key("title", "summary"))
        self.assertNotEqual(translation_key("title", "summary"), translation_key("title", "changed"))
        self.assertNotEqual(translation_key(" title", "summary"), translation_key("title", "summary"))

    def test_cve_and_version_integrity_and_korean_month_conversion(self) -> None:
        original = NewsTranslationInput("id", "CVE-2026-1234", "Product 1.2 was updated on October 20, 2026.")
        self.assertTrue(valid_translation(original, NewsTranslation("id", original.title, "제품 1.2는 2026년 10월 20일 업데이트되었습니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("id", "CVE-2026-9999", "제품 1.2는 2026년 10월 20일 업데이트되었습니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("id", original.title, "제품 1.3은 2026년 10월 20일 업데이트되었습니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("other", original.title, "한국어")))

    def test_korean_prose_with_product_names_does_not_need_translation(self) -> None:
        item = SecurityNewsItem("one", "google-security", "news", "Android 보안 업데이트 안내", "제품의 보안 취약점을 해결하는 업데이트입니다.", "https://example.com")
        self.assertFalse(needs_translation(item))

    def test_unchanged_short_english_prose_is_not_permanently_cached_as_translated(self) -> None:
        original = NewsTranslationInput("short", "Data leak", "Account takeover")
        self.assertFalse(valid_translation(original, NewsTranslation("short", original.title, original.summary)))
