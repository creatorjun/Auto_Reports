# backend/tests/test_security_news_translation.py
import asyncio
import hashlib
import json
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
            "first", "cisco", "advisory", "CVE-2026-1234 critical security issue",
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
            NewsTranslation(value.key, "", (value.summary or value.title) + " 한국어")
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
            return tuple(NewsTranslation(value.key, "", (value.summary or value.title) + " 한국어") for value in inputs)

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
        self.assertIsNone(items[0].title_ko)
        self.assertTrue(items[0].summary_ko.endswith("한국어"))
        self.assertEqual("", self.scalar("SELECT title_ko FROM translations"))
        self.assertEqual(1, state.translated_count)
        self.assertEqual(0, state.pending_count)
        self.assertEqual(1, self.scalar("SELECT COUNT(*) FROM translations"))

    async def test_mixed_items_translate_advisories_and_news_but_never_cve_records(self) -> None:
        service, provider, _ = self.service()
        cve = replace(self.item, id="cve", source_id="nvd", kind="cve", title="CVE-2026-5678 vulnerability")
        news = replace(self.item, id="news", source_id="public-news", kind="news", title="Security news about CVE-2026-1234")
        initial, (items, state) = await self.finish(service, (cve, self.item, news))
        self.assertEqual(2, initial[1].pending_count)
        self.assertEqual([self.item.title, news.title], [value.title for value in provider.translate.await_args.args[0]])
        self.assertIsNone(items[0].title_ko)
        self.assertIsNone(items[0].summary_ko)
        self.assertIsNotNone(items[1].summary_ko)
        self.assertIsNotNone(items[2].summary_ko)
        self.assertEqual(2, state.translated_count)
        self.assertEqual(0, state.pending_count)

    async def test_cve_only_snapshot_and_restore_never_access_cache_or_provider(self) -> None:
        service, provider, cache = self.service()
        cache.read = AsyncMock(wraps=cache.read)
        cache.reserve = AsyncMock(wraps=cache.reserve)
        cve = replace(self.item, source_id="nvd", kind="cve")
        await service.restore((cve,))
        for start in (True, False, True):
            items, state = service.snapshot((cve,), start=start)
            self.assertIsNone(items[0].title_ko)
            self.assertEqual(0, state.translated_count)
            self.assertEqual(0, state.pending_count)
            self.assertFalse(state.translating)
        self.assertIsNone(service._task)
        cache.read.assert_not_awaited()
        cache.reserve.assert_not_awaited()
        provider.translate.assert_not_awaited()

    async def test_cached_identical_news_translation_never_decorates_cve(self) -> None:
        service, provider, _ = self.service()
        await self.finish(service, (self.item,))
        cve = replace(self.item, kind="cve", title_ko="이전 CVE 번역", summary_ko="이전 요약")
        items, state = service.snapshot((cve, self.item), start=False)
        self.assertIsNone(items[0].title_ko)
        self.assertIsNone(items[0].summary_ko)
        self.assertEqual(self.item.title, items[0].title)
        self.assertEqual(self.item.summary, items[0].summary)
        self.assertIsNotNone(items[1].summary_ko)
        self.assertEqual(1, state.translated_count)
        self.assertEqual(0, state.pending_count)
        provider.translate.assert_awaited_once()

    async def test_item_reclassified_as_cve_while_queued_is_not_sent_to_provider(self) -> None:
        service, provider, cache = self.service()
        entered, release = asyncio.Event(), asyncio.Event()
        reserve = cache.reserve

        async def paused_reserve(inputs, **kwargs):
            result = await reserve(inputs, **kwargs)
            entered.set()
            await release.wait()
            return result

        cache.reserve = paused_reserve
        service.snapshot((self.item,))
        await entered.wait()
        cve = replace(self.item, kind="cve")
        _, state = service.snapshot((cve,))
        self.assertEqual(0, state.pending_count)
        self.assertFalse(state.translating)
        release.set()
        await service._task
        provider.translate.assert_not_awaited()
        self.assertEqual(0, service.snapshot((cve,))[1].translated_count)

    async def test_persisted_cve_translation_is_not_restored_or_counted(self) -> None:
        service, _, cache = self.service()
        key = translation_key(self.item.title, self.item.summary)
        request = NewsTranslationInput(key, self.item.title, self.item.summary)
        await cache.complete((request,), (NewsTranslation(key, "저장된 한국어 제목", "저장된 한국어 요약"),), now=self.now)
        restarted, provider, restored_cache = self.service()
        restored_cache.read = AsyncMock(wraps=restored_cache.read)
        cve = replace(self.item, source_id="nvd", kind="cve")
        await restarted.restore((cve,))
        items, state = restarted.snapshot((cve,), start=False)
        self.assertIsNone(items[0].title_ko)
        self.assertIsNone(items[0].summary_ko)
        self.assertEqual(0, state.translated_count)
        self.assertEqual(0, state.pending_count)
        self.assertFalse(state.translating)
        restored_cache.read.assert_not_awaited()
        provider.translate.assert_not_awaited()

    async def test_read_only_snapshots_never_start_provider_even_after_cooldown(self) -> None:
        service, provider, _ = self.service()
        for _ in range(10):
            self.now += timedelta(days=1)
            _, state = service.snapshot((self.item,), start=False)
            self.assertFalse(state.translating)
            self.assertEqual(1, state.pending_count)
        self.assertIsNone(service._task)
        provider.translate.assert_not_awaited()
        provider.translate.side_effect = NewsTranslationProviderError("quota")
        await self.finish(service, (self.item,))
        provider.translate.assert_awaited_once()
        self.now += timedelta(days=2)
        for _ in range(10):
            self.assertFalse(service.snapshot((self.item,), start=False)[1].translating)
        provider.translate.assert_awaited_once()

    async def test_restore_loads_existing_translations_without_reserving_or_translating_missing(self) -> None:
        service, provider, _ = self.service()
        await self.finish(service, (self.item,))
        restarted, other, cache = self.service()
        cache.reserve = AsyncMock(wraps=cache.reserve)
        missing = replace(self.item, id="missing", title="An untranslated title")
        await restarted.restore((self.item, missing))
        items, state = restarted.snapshot((self.item, missing), start=False)
        self.assertIsNotNone(items[0].summary_ko)
        self.assertIsNone(items[1].title_ko)
        self.assertEqual(1, state.translated_count)
        self.assertEqual(1, state.pending_count)
        self.assertFalse(state.translating)
        other.translate.assert_not_awaited()
        cache.reserve.assert_not_awaited()

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
        self.assertEqual(items[0].summary_ko, items[1].summary_ko)

    async def test_only_changed_original_content_is_translated_again(self) -> None:
        service, provider, _ = self.service()
        await self.finish(service, (self.item,))
        changed_source = replace(self.item, id="changed-id", source_id="public-news")
        await self.finish(service, (changed_source,))
        self.assertEqual(1, provider.translate.await_count)
        changed_content = replace(changed_source, summary="Product 1.3 contains a vulnerability.")
        await self.finish(service, (changed_content,))
        self.assertEqual(2, provider.translate.await_count)
        self.assertEqual(2, self.scalar("SELECT COUNT(*) FROM translations"))

    async def test_legacy_full_translation_is_preserved_and_replaced_by_a_separate_summary(self) -> None:
        service, provider, cache = self.service()
        legacy_key = hashlib.sha256(json.dumps(
            ["ko", self.item.title, self.item.summary], ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        legacy_input = NewsTranslationInput(legacy_key, self.item.title, self.item.summary)
        await cache.complete(
            (legacy_input,), (NewsTranslation(legacy_key, "이전 제목 번역", "이전 전체 본문 번역"),), now=self.now,
        )
        legacy_item = replace(self.item, title_ko="이전 제목 번역", summary_ko="이전 전체 본문 번역")
        await service.restore((legacy_item,))
        items, state = service.snapshot((legacy_item,), start=False)
        self.assertIsNone(items[0].title_ko)
        self.assertIsNone(items[0].summary_ko)
        self.assertEqual(1, state.pending_count)
        provider.translate.assert_not_awaited()
        _, (items, state) = await self.finish(service, (legacy_item,))
        self.assertIsNone(items[0].title_ko)
        self.assertEqual(self.item.summary + " 한국어", items[0].summary_ko)
        self.assertEqual(1, state.translated_count)
        self.assertEqual(2, self.scalar("SELECT COUNT(*) FROM translations"))
        self.assertEqual("이전 제목 번역", (await cache.read((legacy_key,)))[legacy_key].title_ko)

    async def test_new_summary_namespace_preserves_legacy_daily_budget_and_global_pause(self) -> None:
        service, provider, cache = self.service(daily_limit=1)
        legacy_input = NewsTranslationInput("legacy-content-key", self.item.title, self.item.summary)
        await cache.reserve((legacy_input,), now=self.now, daily_limit=1, batch_size=1, minimum_interval_seconds=0, max_attempts=3)
        await cache.complete((legacy_input,), (), now=self.now, failure="billing")
        _, (_, state) = await self.finish(service, (self.item,))
        provider.translate.assert_not_awaited()
        self.assertIn("크레딧", state.message)
        self.assertEqual(1, self.scalar("SELECT SUM(used) FROM request_budget"))
        self.now += timedelta(hours=24)
        await self.finish(service, (self.item,))
        provider.translate.assert_awaited_once()
        self.assertEqual(2, self.scalar("SELECT SUM(used) FROM request_budget"))

    async def test_invalid_new_cache_entry_is_not_restored_as_a_summary(self) -> None:
        service, provider, cache = self.service()
        key = translation_key(self.item.title, self.item.summary)
        request = NewsTranslationInput(key, self.item.title, self.item.summary)
        await cache.complete((request,), (NewsTranslation(key, "전체 제목 번역", "전체 본문 번역"),), now=self.now)
        await service.restore((self.item,))
        items, state = service.snapshot((self.item,), start=False)
        self.assertIsNone(items[0].title_ko)
        self.assertIsNone(items[0].summary_ko)
        self.assertEqual(0, state.translated_count)
        provider.translate.assert_not_awaited()

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
                NewsTranslation(inputs[0].key, "", inputs[0].summary + " 한국어"),
                NewsTranslation(inputs[1].key, "", "제품 99.99에 대한 잘못된 응답"),
            )

        provider.translate.side_effect = translate
        _, (items, state) = await self.finish(service, (self.item, second))
        self.assertIsNotNone(items[0].summary_ko)
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
        await cache.complete((request,), (NewsTranslation(request.key, "", request.summary + " 한국어"),), now=self.now)
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
        self.assertIsNotNone(service.snapshot((second,))[0][0].summary_ko)

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

    async def test_korean_items_skip_provider_and_english_title_only_items_get_summaries(self) -> None:
        service, provider, _ = self.service()
        korean = replace(self.item, source_id="kisa", title="보안 업데이트 권고", summary="")
        items, state = service.snapshot((korean,))
        self.assertFalse(state.translating)
        self.assertEqual(0, state.pending_count)
        provider.translate.assert_not_awaited()
        title_only = replace(self.item, summary="")
        _, (items, _) = await self.finish(service, (title_only,))
        self.assertEqual(title_only.title + " 한국어", items[0].summary_ko)
        self.assertIsNone(items[0].title_ko)

    async def test_korean_original_skips_ai_while_english_news_is_translated(self) -> None:
        service, provider, _ = self.service()
        korean = replace(
            self.item, id="korean-news", source_id="public-news", kind="news",
            title="안드로이드의 새로운 보안 및 개인정보 보호 기능을 소개합니다",
            summary="안드로이드가 이용자들을 더 안전하게 보호하기 위해 도입하는 새로운 기능들을 확인하세요.",
            url="https://example.com/ko/security/",
        )
        english = replace(self.item, source_id="public-news", kind="news")
        initial, (items, state) = await self.finish(service, (korean, english))
        self.assertEqual(1, initial[1].pending_count)
        provider.translate.assert_awaited_once()
        self.assertEqual([english.title], [value.title for value in provider.translate.await_args.args[0]])
        self.assertEqual(korean, items[0])
        self.assertIsNone(items[0].title_ko)
        self.assertIsNotNone(items[1].summary_ko)
        self.assertEqual(1, state.translated_count)
        self.assertEqual(0, state.pending_count)


class TranslationValidationTest(unittest.TestCase):
    def test_summary_hash_is_stable_content_based_and_separate_from_legacy_translation(self) -> None:
        self.assertEqual(translation_key("title", "summary"), translation_key("title", "summary"))
        self.assertNotEqual(translation_key("title", "summary"), translation_key("title", "changed"))
        self.assertNotEqual(translation_key(" title", "summary"), translation_key("title", "summary"))
        legacy_key = hashlib.sha256(b'["ko","title","summary"]').hexdigest()
        self.assertNotEqual(legacy_key, translation_key("title", "summary"))

    def test_summary_may_omit_details_but_must_not_invent_cves_or_numbers(self) -> None:
        original = NewsTranslationInput("id", "CVE-2026-1234", "Product 1.2 was updated on October 20, 2026.")
        self.assertTrue(valid_translation(original, NewsTranslation("id", "", "제품 업데이트가 제공되었습니다.")))
        self.assertTrue(valid_translation(original, NewsTranslation("id", "", "제품 1.2의 CVE-2026-1234 대응 업데이트가 제공되었습니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("id", "", "CVE-2026-9999 대응 업데이트입니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("id", "", "제품 1.3 대응 업데이트입니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("id", "", "제품 취약점 50건을 해결했습니다.")))
        self.assertFalse(valid_translation(original, NewsTranslation("other", "", "한국어 요약입니다.")))

    def test_summary_rejects_full_titles_multiline_overlength_html_and_non_korean(self) -> None:
        original = NewsTranslationInput("id", "Security update", "An update resolves a product vulnerability.")
        self.assertTrue(valid_translation(original, NewsTranslation("id", "", "한" * 180)))
        for title, summary in (
            ("별도 번역 제목", "보안 업데이트입니다."),
            ("", ""), ("", " "), ("", "한" * 181), ("", "Security update"),
            ("", "보안 문제\n업데이트"), ("", "보안 문제\r업데이트"), ("", "보안 문제\u2028업데이트"),
            ("", "<b>보안 업데이트</b>"), ("", "```보안 업데이트```"),
        ):
            with self.subTest(title=title, summary=summary):
                self.assertFalse(valid_translation(original, NewsTranslation("id", title, summary)))

    def test_removed_google_source_never_needs_summary(self) -> None:
        item = SecurityNewsItem("old", "google-security", "news", "Security update", "A product update.", "https://example.com")
        self.assertFalse(needs_translation(item))

    def test_korean_prose_with_product_names_does_not_need_translation(self) -> None:
        item = SecurityNewsItem("one", "public-news", "news", "Android 보안 업데이트 안내", "제품의 보안 취약점을 해결하는 업데이트입니다.", "https://example.com")
        self.assertFalse(needs_translation(item))

    def test_unchanged_short_english_prose_is_not_permanently_cached_as_translated(self) -> None:
        original = NewsTranslationInput("short", "Data leak", "Account takeover")
        self.assertFalse(valid_translation(original, NewsTranslation("short", original.title, original.summary)))
