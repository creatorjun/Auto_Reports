# backend/tests/test_security_news_snapshot_store.py
import asyncio
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from src.application.services.security_news_translation import SecurityNewsTranslationService, translation_key
from src.application.use_cases.security_news import SecurityNewsRefreshThrottled, SecurityNewsUseCase
from src.domain.entities.security_news import SecurityNewsItem, SecurityNewsSource, SecurityNewsSourceResult
from src.domain.entities.security_news_translation import NewsTranslation, NewsTranslationInput
from src.infrastructure.persistence.security_news_snapshot_store import SqliteSecurityNewsSnapshotStore
from src.infrastructure.persistence.security_news_translation_cache import SqliteNewsTranslationCache


class SecurityNewsSnapshotStoreTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "news.sqlite3")
        self.now = datetime(2026, 10, 20, 23, tzinfo=timezone.utc)
        self.item = SecurityNewsItem(
            "nvd:CVE-2026-1234", "nvd", "cve", "Security issue", "Product 1.2 issue",
            "https://nvd.nist.gov/vuln/detail/CVE-2026-1234",
            published_at=self.now, cve_ids=("CVE-2026-1234",), cvss_score=9.8, severity="critical",
        )
        self.results = {
            "nvd": SecurityNewsSourceResult((self.item,), warning="최신 항목"),
            "cisa-kev": SecurityNewsSourceResult((), frozenset({"CVE-2026-1234"})),
        }

    def service(self, *, translation=None, store=None):
        source = AsyncMock()
        source.sources = (
            SecurityNewsSource("cisa-kev", "KEV", "https://cisa.gov/", "cve"),
            SecurityNewsSource("nvd", "NVD", "https://nvd.nist.gov/", "cve", minimum_refresh_seconds=7200),
        )
        source.fetch.side_effect = lambda source_id: self.results[source_id]
        store = store if store is not None else SqliteSecurityNewsSnapshotStore(self.path)
        service = SecurityNewsUseCase(source, clock=lambda: self.now, translation=translation, store=store)
        self.addAsyncCleanup(store.aclose)
        self.addAsyncCleanup(service.aclose)
        return service, source, store

    async def manual(self, service):
        await service.get_snapshot(refresh=True)
        await service._task
        return await service.get_snapshot()

    async def test_fresh_store_and_restart_restore_do_not_collect(self) -> None:
        service, source, store = self.service()
        self.assertIsNone(await store.load())
        await service.initialize()
        self.assertFalse((await service.get_snapshot()).initialized)
        source.fetch.assert_not_awaited()
        first = await self.manual(service)
        await service.aclose()
        await store.aclose()
        restarted, other, restored_store = self.service()
        await asyncio.gather(*(restarted.initialize() for _ in range(10)))
        restored = await restarted.get_snapshot()
        self.assertEqual(first, restored)
        self.assertTrue(restored.items[0].known_exploited)
        self.assertEqual(("CVE-2026-1234",), restored.items[0].cve_ids)
        self.assertEqual("최신 항목", next(value for value in restored.sources if value.id == "nvd").warning)
        self.assertEqual(self.now, dict((await restored_store.load()).source_attempts)["nvd"])
        for _ in range(10):
            self.now += timedelta(days=1)
            await restarted.get_snapshot()
        other.fetch.assert_not_awaited()

    async def test_manual_cooldown_and_nvd_interval_survive_restart(self) -> None:
        service, _, _ = self.service()
        await self.manual(service)
        await service.aclose()
        self.now += timedelta(seconds=30)
        restarted, source, _ = self.service()
        with self.assertRaises(SecurityNewsRefreshThrottled) as caught:
            await restarted.get_snapshot(refresh=True)
        self.assertEqual(30, caught.exception.retry_after_seconds)
        source.fetch.assert_not_awaited()
        self.now += timedelta(seconds=30)
        await self.manual(restarted)
        self.assertEqual(["cisa-kev"], [call.args[0] for call in source.fetch.await_args_list])

    async def test_daily_claim_survives_restart_but_manual_refresh_remains_available(self) -> None:
        service, source, _ = self.service()
        await service.refresh_scheduled()
        self.assertEqual(2, source.fetch.await_count)
        await service.aclose()
        self.now += timedelta(hours=3)
        restarted, other, _ = self.service()
        await restarted.refresh_scheduled()
        other.fetch.assert_not_awaited()
        await self.manual(restarted)
        self.assertEqual(2, other.fetch.await_count)
        self.now += timedelta(hours=21)
        await restarted.refresh_scheduled()
        self.assertEqual(4, other.fetch.await_count)

    async def test_concurrent_store_instances_claim_same_day_only_once(self) -> None:
        stores = [SqliteSecurityNewsSnapshotStore(self.path) for _ in range(12)]
        for store in stores:
            self.addAsyncCleanup(store.aclose)
        day = date(2026, 10, 21)
        claims = await asyncio.gather(*(store.claim_daily_refresh(day) for store in stores))
        self.assertEqual(1, sum(claims))
        self.assertFalse(await stores[0].claim_daily_refresh(day - timedelta(days=1)))
        self.assertTrue(await stores[0].claim_daily_refresh(day + timedelta(days=1)))
        self.assertFalse(await stores[-1].claim_daily_refresh(day + timedelta(days=1)))

    async def test_cancelled_collection_preserves_attempts_and_partial_results(self) -> None:
        service, source, store = self.service()
        await self.manual(service)
        previous_success = self.now
        self.now += timedelta(hours=2)
        attempt = self.now
        entered, partial = asyncio.Event(), asyncio.Event()
        updated = replace(self.item, id="cisa:updated", source_id="cisa-kev", title="Updated public advisory")

        async def fetch(source_id):
            if source_id == "cisa-kev":
                partial.set()
                return SecurityNewsSourceResult((updated,))
            entered.set()
            await asyncio.Event().wait()

        source.fetch.side_effect = fetch
        await service.get_snapshot(refresh=True)
        await entered.wait()
        await partial.wait()
        self.assertEqual(attempt, dict((await store.load()).source_attempts)["nvd"])
        await service.aclose()
        self.now += timedelta(seconds=60)
        restarted, other, _ = self.service()
        snapshot = await restarted.get_snapshot()
        self.assertEqual({self.item.id, updated.id}, {item.id for item in snapshot.items})
        self.assertEqual(previous_success, snapshot.refreshed_at)
        await self.manual(restarted)
        self.assertEqual(["cisa-kev"], [call.args[0] for call in other.fetch.await_args_list])

    async def test_shutdown_during_failed_store_write_preserves_cancellation_without_fetching(self) -> None:
        service, source, store = self.service()
        await service.initialize()
        entered, release = threading.Event(), threading.Event()

        def failed_save(snapshot):
            entered.set()
            release.wait(timeout=5)
            raise OSError("storage failure during shutdown")

        store._save = failed_save
        await service.get_snapshot(refresh=True)
        self.assertTrue(await asyncio.to_thread(entered.wait, 5))
        closing = asyncio.create_task(service.aclose())
        try:
            await asyncio.sleep(0)
            self.assertTrue(service._closed)
            self.assertGreater(service._task.cancelling(), 0)
        finally:
            release.set()
            await asyncio.wait_for(closing, timeout=5)
        self.assertTrue(service._task.cancelled())
        source.fetch.assert_not_awaited()

    async def test_store_failure_does_not_trigger_get_or_unreserved_automatic_collection(self) -> None:
        store = AsyncMock()
        store.load.side_effect = OSError("private-path")
        store.claim_daily_refresh.side_effect = OSError("private-path")
        store.save.side_effect = OSError("private-path")
        service, source, _ = self.service(store=store)
        with self.assertLogs("src.application.use_cases.security_news", level="WARNING") as logs:
            await service.initialize()
            await service.get_snapshot()
            await service.refresh_scheduled()
            source.fetch.assert_not_awaited()
            result = await self.manual(service)
        self.assertEqual(1, len(result.items))
        self.assertNotIn("private-path", " ".join(logs.output))
        self.assertEqual(2, source.fetch.await_count)

    async def test_corrupt_snapshot_is_empty_until_manual_collection_without_crashing(self) -> None:
        service, source, store = self.service()
        await store.load()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("INSERT INTO news_snapshot VALUES (1, ?)", ("not-json",))
            connection.commit()
        with self.assertLogs("src.application.use_cases.security_news", level="WARNING"):
            self.assertFalse((await service.get_snapshot()).initialized)
        source.fetch.assert_not_awaited()
        self.assertEqual(1, len((await self.manual(service)).items))

    async def test_restart_restores_translation_locally_without_new_provider_work(self) -> None:
        self.item = replace(self.item, kind="advisory")
        self.results["nvd"] = SecurityNewsSourceResult((self.item,), warning="최신 항목")
        cache = SqliteNewsTranslationCache(str(Path(self.directory.name) / "translations.sqlite3"))
        self.addAsyncCleanup(cache.aclose)
        key = translation_key(self.item.title, self.item.summary)
        request = NewsTranslationInput(key, self.item.title, self.item.summary)
        await cache.complete((request,), (NewsTranslation(key, "보안 문제", "제품 1.2 문제"),), now=self.now)
        service, _, _ = self.service()
        await self.manual(service)
        await service.aclose()
        provider = AsyncMock()
        translation = SecurityNewsTranslationService(provider, cache, clock=lambda: self.now)
        self.addAsyncCleanup(translation.aclose)
        restarted, source, _ = self.service(translation=translation)
        snapshot = await restarted.get_snapshot()
        self.assertEqual("보안 문제", snapshot.items[0].title_ko)
        self.assertEqual(1, snapshot.translation.translated_count)
        self.assertFalse(snapshot.translation.translating)
        self.now += timedelta(days=2)
        for _ in range(10):
            await restarted.get_snapshot()
        source.fetch.assert_not_awaited()
        provider.translate.assert_not_awaited()

    async def test_closed_store_refuses_read_write_and_claim(self) -> None:
        service, _, store = self.service()
        await self.manual(service)
        snapshot = await store.load()
        await store.aclose()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await store.load()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await store.save(snapshot)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await store.claim_daily_refresh(self.now.date())
