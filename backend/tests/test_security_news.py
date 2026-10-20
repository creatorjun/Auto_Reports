# backend/tests/test_security_news.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from src.application.use_cases.security_news import SecurityNewsRefreshThrottled, SecurityNewsUseCase
from src.domain.entities.security_news import SecurityNewsItem, SecurityNewsSource, SecurityNewsSourceResult


class SecurityNewsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        self.port = AsyncMock()
        self.port.sources = (
            SecurityNewsSource("cisa-kev", "KEV", "https://cisa.gov/", "cve"),
            SecurityNewsSource("nvd", "NVD", "https://nvd.nist.gov/", "cve", minimum_refresh_seconds=7200),
        )
        self.item = SecurityNewsItem(
            "nvd:CVE-2026-1234", "nvd", "cve", "Test", "Summary",
            "https://nvd.nist.gov/vuln/detail/CVE-2026-1234",
            published_at=self.now, cve_ids=("CVE-2026-1234",),
        )
        self.results = {
            "nvd": SecurityNewsSourceResult((self.item,)),
            "cisa-kev": SecurityNewsSourceResult((), frozenset({"CVE-2026-1234"})),
        }
        self.port.fetch.side_effect = lambda source_id: self.results[source_id]
        self.use_case = SecurityNewsUseCase(self.port, clock=lambda: self.now)

    async def asyncTearDown(self) -> None:
        await self.use_case.aclose()

    async def complete_refresh(self, *, manual: bool = False):
        await self.use_case.get_snapshot(refresh=manual)
        await self.use_case._task
        return await self.use_case.get_snapshot()

    async def test_initial_response_does_not_wait_for_sources(self) -> None:
        gate = asyncio.Event()

        async def fetch(source_id):
            await gate.wait()
            return self.results[source_id]

        self.port.fetch.side_effect = fetch
        snapshot = await asyncio.wait_for(self.use_case.get_snapshot(), timeout=0.1)
        self.assertFalse(snapshot.initialized)
        self.assertTrue(snapshot.refreshing)
        self.assertEqual({"pending"}, {state.status for state in snapshot.sources})
        gate.set()
        await self.use_case._task
        self.assertTrue((await self.use_case.get_snapshot()).initialized)

    async def test_parallel_get_and_refresh_share_one_collection(self) -> None:
        await asyncio.gather(*(self.use_case.get_snapshot(refresh=True) for _ in range(20)))
        await self.use_case._task
        self.assertEqual(2, self.port.fetch.await_count)

    async def test_kev_enriches_matching_nvd_items_even_without_visible_kev_rows(self) -> None:
        snapshot = await self.complete_refresh()
        self.assertTrue(snapshot.items[0].known_exploited)
        self.assertFalse(self.item.known_exploited)
        self.assertEqual(self.now, snapshot.refreshed_at)
        self.assertEqual(self.now + timedelta(seconds=60), snapshot.next_refresh_at)

    async def test_cached_get_does_not_fetch_and_automatic_refresh_obeys_interval(self) -> None:
        await self.complete_refresh()
        self.now += timedelta(seconds=899)
        self.assertFalse((await self.use_case.get_snapshot()).refreshing)
        self.assertEqual(2, self.port.fetch.await_count)
        self.now += timedelta(seconds=1)
        self.assertTrue((await self.use_case.get_snapshot()).refreshing)
        await self.use_case._task
        self.assertEqual(3, self.port.fetch.await_count)

    async def test_manual_refresh_throttles_and_preserves_nvd_two_hour_interval(self) -> None:
        await self.complete_refresh()
        self.now += timedelta(seconds=1)
        with self.assertRaises(SecurityNewsRefreshThrottled) as caught:
            await self.use_case.get_snapshot(refresh=True)
        self.assertEqual(59, caught.exception.retry_after_seconds)
        self.now += timedelta(seconds=59)
        await self.complete_refresh(manual=True)
        self.assertEqual(["cisa-kev", "nvd", "cisa-kev"], [call.args[0] for call in self.port.fetch.await_args_list])
        self.now += timedelta(hours=2)
        await self.complete_refresh(manual=True)
        self.assertEqual(2, sum(call.args[0] == "nvd" for call in self.port.fetch.await_args_list))

    async def test_source_failure_retains_last_successful_items_and_time(self) -> None:
        await self.complete_refresh()
        first_success = self.now
        self.now += timedelta(hours=2)

        async def fetch(source_id):
            if source_id == "nvd":
                raise TimeoutError("secret proxy credentials")
            return self.results[source_id]

        self.port.fetch.side_effect = fetch
        snapshot = await self.complete_refresh(manual=True)
        nvd = next(source for source in snapshot.sources if source.id == "nvd")
        self.assertEqual("stale", nvd.status)
        self.assertEqual(first_success, nvd.last_success_at)
        self.assertEqual(1, len(snapshot.items))
        self.assertNotIn("secret", nvd.error)
        self.assertEqual("ok", next(source for source in snapshot.sources if source.id == "cisa-kev").status)

    async def test_first_failure_is_error_and_does_not_retry_on_every_get(self) -> None:
        self.port.fetch.side_effect = TimeoutError()
        snapshot = await self.complete_refresh()
        self.assertTrue(snapshot.initialized)
        self.assertEqual({"error"}, {source.status for source in snapshot.sources})
        for _ in range(10):
            await self.use_case.get_snapshot()
        self.assertEqual(2, self.port.fetch.await_count)

    async def test_duplicate_source_ids_and_dates_are_sorted(self) -> None:
        older = replace(self.item, id="nvd:older", published_at=self.now - timedelta(days=1))
        unknown = replace(self.item, id="nvd:unknown", published_at=None)
        self.results["nvd"] = SecurityNewsSourceResult((older, self.item, unknown, self.item))
        snapshot = await self.complete_refresh()
        self.assertEqual([self.item.id, older.id, unknown.id], [item.id for item in snapshot.items])
        self.assertEqual(3, next(source for source in snapshot.sources if source.id == "nvd").count)

    async def test_shutdown_cancels_all_inflight_sources_without_closing_owned_adapter(self) -> None:
        started = asyncio.Event()
        cancelled: list[str] = []

        async def fetch(source_id):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(source_id)

        self.port.fetch.side_effect = fetch
        await self.use_case.get_snapshot()
        await started.wait()
        await self.use_case.aclose()
        self.assertEqual({"cisa-kev", "nvd"}, set(cancelled))
        self.port.aclose.assert_not_awaited()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await self.use_case.get_snapshot()
