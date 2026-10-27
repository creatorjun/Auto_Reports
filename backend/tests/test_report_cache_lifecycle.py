# backend/tests/test_report_cache_lifecycle.py
import asyncio
import unittest
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import date
from unittest.mock import AsyncMock

from src.application.ports.report_repository import ReportRepository
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.refresh_report import RefreshReportUseCase
from src.domain.entities.report import NewReport, Report
from src.infrastructure.report_cache import ReportLruCache


class ReportCacheLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache = ReportLruCache(ttl_seconds=10, stale_ttl_seconds=20)
        self.addAsyncCleanup(self.cache.aclose)
        self.report = Report(
            id=1, week_start=date(2026, 10, 19), week_end=date(2026, 10, 25),
            report_date="2026-10-21 12:00", widgets={},
        )

    async def test_forced_latest_read_uses_persisted_report_despite_warm_previous_pointer(self):
        previous = replace(self.report, id=2, week_start=date(2026, 10, 5), week_end=date(2026, 10, 11))
        await self.cache.set(previous.id, previous)
        await self.cache.set_latest_id(previous.id)
        repository = AsyncMock(spec=ReportRepository)
        repository.find_latest.return_value = self.report
        use_case = GetReportUseCase(repository, self.cache)

        self.assertEqual(previous, await use_case.get_latest())
        repository.find_latest.assert_not_awaited()
        self.assertEqual(self.report, await use_case.get_latest(bypass_cache=True))
        repository.find_latest.assert_awaited_once_with()
        self.assertEqual(self.report.id, await self.cache.get_latest_id())

    async def test_forced_latest_read_never_falls_back_to_cached_deleted_or_unavailable_report(self):
        await self.cache.set(self.report.id, self.report)
        await self.cache.set_latest_id(self.report.id)
        repository = AsyncMock(spec=ReportRepository)
        repository.find_latest.return_value = None
        use_case = GetReportUseCase(repository, self.cache)

        self.assertIsNone(await use_case.get_latest(bypass_cache=True))
        repository.find_latest.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await use_case.get_latest(bypass_cache=True)

    async def test_refresh_started_before_generation_preserves_new_latest_pointer(self):
        previous = replace(self.report, id=2, week_start=date(2026, 10, 5), week_end=date(2026, 10, 11))
        repository = AsyncMock(spec=ReportRepository)
        repository.find_latest.return_value = previous
        repository.find_annual.return_value = None
        repository.update_widgets.return_value = previous
        entered, release = asyncio.Event(), asyncio.Event()

        async def collect(**kwargs):
            entered.set()
            await release.wait()
            return NewReport(
                week_start=previous.week_start, week_end=previous.week_end,
                report_date=previous.report_date,
            )

        assembler = AsyncMock()
        assembler.collect.side_effect = collect
        await self.cache.set(previous.id, previous)
        await self.cache.set_latest_id(previous.id)
        task = asyncio.create_task(RefreshReportUseCase(assembler, repository, self.cache).execute())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            repository.find_latest.return_value = self.report
            await self.cache.set(self.report.id, self.report)
            await self.cache.set_latest_id(self.report.id)
        finally:
            release.set()
            await asyncio.wait_for(task, 1)

        self.assertEqual(self.report.id, await self.cache.get_latest_id())
        self.assertEqual(self.report, await GetReportUseCase(repository, self.cache).get_latest())
        repository.update_widgets.assert_awaited_once()
        self.assertEqual(previous.id, repository.update_widgets.await_args.args[0])

    async def test_unconfigured_refresh_never_detaches_the_request_repository(self):
        entered, cancelled = asyncio.Event(), asyncio.Event()
        request_open = False
        events = []
        repository = AsyncMock(spec=ReportRepository)

        async def find(report_id):
            self.assertTrue(request_open)
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.assertTrue(request_open)
                events.append("query cancelled")
                cancelled.set()
                raise

        repository.find_by_id.side_effect = find

        async def request():
            nonlocal request_open
            request_open = True
            try:
                return await GetReportUseCase(repository, self.cache).get_by_id(1)
            finally:
                request_open = False
                events.append("request session closed")

        task = asyncio.create_task(request())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cancelled.is_set())
        self.assertEqual(["query cancelled", "request session closed"], events)
        self.assertFalse(self.cache._cache._tasks)

    async def test_cancelled_request_does_not_close_the_shared_refresh_session(self):
        entered, release, refresh_closed = asyncio.Event(), asyncio.Event(), asyncio.Event()
        open_sessions = set()
        repository = AsyncMock(spec=ReportRepository)

        @asynccontextmanager
        async def session(name):
            open_sessions.add(name)
            try:
                yield
            finally:
                open_sessions.remove(name)
                if name == "refresh":
                    refresh_closed.set()

        async def refresh(report_id):
            async with session("refresh"):
                entered.set()
                await release.wait()
                self.assertEqual({"refresh", "second request"}, open_sessions)
                return self.report

        async def request(name):
            async with session(name):
                return await GetReportUseCase(repository, self.cache, refresh_report=refresh).get_by_id(1)

        first = asyncio.create_task(request("first request"))
        await entered.wait()
        second = asyncio.create_task(request("second request"))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(refresh_closed.is_set())
        release.set()
        self.assertEqual(self.report, await asyncio.wait_for(second, 1))
        self.assertTrue(refresh_closed.is_set())
        self.assertFalse(open_sessions)
        repository.find_by_id.assert_not_awaited()

    async def test_stale_response_can_close_request_before_its_separate_refresh_finishes(self):
        cached = replace(self.report, report_date="2026-10-20 12:00")
        self.cache._cache._ttl = -1
        await self.cache.set(1, cached)
        await self.cache.set_latest_id(1)
        entered, release = asyncio.Event(), asyncio.Event()
        request_open = True
        refresh_open = False
        repository = AsyncMock(spec=ReportRepository)

        async def refresh(report_id):
            nonlocal refresh_open
            refresh_open = True
            try:
                entered.set()
                await release.wait()
                self.assertFalse(request_open)
                return self.report
            finally:
                refresh_open = False

        use_case = GetReportUseCase(repository, self.cache, refresh_report=refresh)
        self.assertEqual(cached, await use_case.get_latest())
        request_open = False
        await entered.wait()
        self.assertTrue(refresh_open)
        flight = self.cache._cache._inflight[1]
        release.set()
        await asyncio.wait_for(flight, 1)
        self.assertFalse(refresh_open)
        self.assertEqual(self.report, await self.cache.get(1))
        repository.find_by_id.assert_not_awaited()
        repository.find_latest.assert_not_awaited()

    async def test_failed_independent_refresh_preserves_request_repository_fallback(self):
        repository = AsyncMock(spec=ReportRepository)
        repository.find_by_id.return_value = self.report
        refresh = AsyncMock(side_effect=RuntimeError("independent session unavailable"))

        with self.assertLogs("src.application.use_cases.get_report", level="ERROR"):
            report = await GetReportUseCase(repository, self.cache, refresh_report=refresh).get_by_id(1)

        self.assertEqual(self.report, report)
        refresh.assert_awaited_once_with(1)
        repository.find_by_id.assert_awaited_once_with(1)
        self.assertEqual(self.report, await self.cache.get(1))
