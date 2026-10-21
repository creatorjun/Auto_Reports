# backend/tests/test_lru_cache_lifecycle.py
import asyncio
import unittest

from src.infrastructure.cache.lru_cache import LruCache


class LruCacheLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache = LruCache(ttl_seconds=10, stale_ttl_seconds=20)
        self.addAsyncCleanup(self.cache.aclose)

    async def test_cancelled_initial_request_does_not_strand_shared_fetch(self):
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def fetch(key):
            calls.append(key)
            entered.set()
            await release.wait()
            return "fresh"

        first = asyncio.create_task(self.cache.async_get("issue", fetch))
        await entered.wait()
        second = asyncio.create_task(self.cache.async_get("issue", fetch))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        release.set()
        self.assertEqual("fresh", await asyncio.wait_for(second, 1))
        self.assertEqual(["issue"], calls)
        self.assertEqual("fresh", await self.cache.async_get("issue"))
        self.assertFalse(self.cache._inflight)

    async def test_cancelled_waiter_does_not_cancel_shared_fetch(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def fetch(key):
            entered.set()
            await release.wait()
            return "fresh"

        first = asyncio.create_task(self.cache.async_get("issue", fetch))
        await entered.wait()
        waiter = asyncio.create_task(self.cache.async_get("issue", fetch))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        release.set()
        self.assertEqual("fresh", await asyncio.wait_for(first, 1))

    async def test_close_cancels_and_drains_owned_fetch_before_returning(self):
        entered, cancelled, cleanup = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def fetch(key):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                await cleanup.wait()
                raise

        request = asyncio.create_task(self.cache.async_get("issue", fetch))
        await entered.wait()
        close = asyncio.create_task(self.cache.aclose())
        await cancelled.wait()
        self.assertFalse(close.done())
        cleanup.set()
        await asyncio.wait_for(close, 1)
        self.assertIsNone(await request)
        self.assertFalse(self.cache._tasks)
        self.assertFalse(self.cache._inflight)

    async def test_cancellation_resistant_fetch_cannot_restore_erased_personal_data(self):
        entered = asyncio.Event()

        async def fetch(key):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return "erased-person-name"

        request = asyncio.create_task(self.cache.async_get("issue", fetch))
        await entered.wait()
        await self.cache.aclose()
        self.assertIsNone(await request)
        self.assertIsNone(await self.cache.async_get("issue"))

    async def test_invalidated_fetch_cannot_replace_or_remove_new_flight(self):
        entered, cancelled, old_release, new_entered, new_release = (
            asyncio.Event() for _ in range(5)
        )

        async def old_fetch(key):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                await old_release.wait()
                return "old"

        async def new_fetch(key):
            new_entered.set()
            await new_release.wait()
            return "current"

        old_request = asyncio.create_task(self.cache.async_get("issue", old_fetch))
        await entered.wait()
        await self.cache.async_invalidate_all()
        await cancelled.wait()
        new_request = asyncio.create_task(self.cache.async_get("issue", new_fetch))
        await new_entered.wait()
        flight = self.cache._inflight["issue"]
        old_release.set()
        self.assertIsNone(await old_request)
        self.assertIs(flight, self.cache._inflight["issue"])
        new_release.set()
        self.assertEqual("current", await new_request)
        self.assertEqual("current", await self.cache.async_get("issue"))

    async def test_delete_prevents_inflight_value_from_returning(self):
        entered = asyncio.Event()

        async def fetch(key):
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return "deleted"

        request = asyncio.create_task(self.cache.async_get("issue", fetch))
        await entered.wait()
        await self.cache.async_delete("issue")
        self.assertIsNone(await request)
        self.assertIsNone(await self.cache.async_get("issue"))

    async def test_stale_refresh_is_single_flight_and_close_does_not_restore_value(self):
        entered = asyncio.Event()
        calls = []

        async def fetch(key):
            calls.append(key)
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return "old-person-name"

        self.cache._ttl = -1
        await self.cache.async_set("issue", "cached")
        self.assertEqual("cached", await self.cache.async_get("issue", fetch))
        await entered.wait()
        self.assertEqual("cached", await self.cache.async_get("issue", fetch))
        await self.cache.aclose()
        self.assertEqual(["issue"], calls)
        self.assertIsNone(await self.cache.async_get("issue"))

    async def test_failed_fetch_releases_flight_and_can_retry(self):
        async def failing(key):
            raise RuntimeError("source unavailable")

        async def healthy(key):
            return "fresh"

        with self.assertLogs("src.infrastructure.cache.lru_cache", level="ERROR"):
            self.assertIsNone(await self.cache.async_get("issue", failing))
        self.assertFalse(self.cache._inflight)
        self.assertEqual("fresh", await self.cache.async_get("issue", healthy))
