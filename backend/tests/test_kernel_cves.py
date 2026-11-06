# backend/tests/test_kernel_cves.py
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from src.application.services.daily_advisories import scheduled_day
from src.application.use_cases.kernel_cves import KernelCveUseCase
from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeed, KernelFeedData, KernelSnapshot, KernelTarget
from src.infrastructure.persistence.kernel_cve_store import SqliteKernelSnapshotStore
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.v1.router import router


FEED = KernelFeed("vendor", "Vendor", "https://vendor.example/feed")
TARGET = KernelTarget("test-8", "Test Linux 8", ("kernel",), ("x86_64",), (FEED,), "공급사 보안 공지")
BUILD = KernelBuild("kernel", "x86_64", "2")


def advisory(cve: str, fixed: str, **changes):
    return replace(KernelAdvisory(cve, "high", "ERR-"+fixed, "https://vendor.example/notice", "2026-01-01",
                                  "kernel", "x86_64", fixed), **changes)


class FakeSource:
    targets = (TARGET, replace(TARGET, id="unavailable", available=False))

    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.fail = False
        self.calls = 0
        self.data = KernelFeedData((
            advisory("CVE-2026-1000", "1"), advisory("CVE-2026-1000", "8"),
            advisory("CVE-2026-1001", "4"), advisory("CVE-2026-1001", "4"),
            advisory("CVE-2026-1002", "5", severity="low", title="Kernel timer update"),
            advisory("CVE-2026-1003", "3", architecture="aarch64"),
            advisory("CVE-2026-1004", "3", package="kernel-uek"),
        ), (BUILD, replace(BUILD, version="10"), replace(BUILD, version="2", architecture="aarch64")))

    async def fetch(self, target, feed):
        self.calls += 1
        self.started.set()
        await self.release.wait()
        if self.fail:
            raise RuntimeError("fixture failed")
        return self.data

    @staticmethod
    def validate(target, build):
        if not build.version.isdecimal():
            raise ValueError("Invalid version")

    @staticmethod
    def same_branch(build, item):
        return build.package == item.package and build.architecture == item.architecture

    @staticmethod
    def matches(target, build, item):
        return int(build.version) < int(item.fixed_version)

    @staticmethod
    def compare_versions(left, right):
        return int(left) - int(right)

    @staticmethod
    def coverage_note(target, build, data):
        return "공급사 미확인 버전" if build.version == "999" else None


class KernelCveTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = SqliteKernelSnapshotStore(str(Path(temp.name)/"snapshots.sqlite3"))
        self.source = FakeSource()
        self.now = datetime(2026, 11, 5, 22, 58, tzinfo=timezone.utc)
        self.service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(self.service.aclose)

    async def find(self, version="2", severity="all", search="", page=1, page_size=10):
        return await self.service.find(TARGET.id, replace(BUILD, version=version), severity, search, page, page_size)

    async def collect(self):
        await self.service.releases(TARGET.id, BUILD.package, BUILD.architecture)
        await self.source.started.wait()
        self.source.release.set()
        await self.service._cache[(TARGET.id, FEED.id)].task

    async def seed(self, data, when):
        claim = await self.store.claim(TARGET.id, FEED.id, scheduled_day(when), "seed", when)
        self.assertTrue(claim.acquired)
        self.assertTrue(await self.store.finish(TARGET.id, FEED.id, "seed", KernelSnapshot(data, when), None))

    async def test_coalesces_first_requests_and_restores_snapshot(self):
        first, second = await asyncio.gather(self.find(), self.find())
        self.assertTrue(first.refreshing)
        self.assertEqual(("pending", None, ()), (second.status, second.total, second.items))
        await self.collect()
        self.assertEqual(1, self.source.calls)
        versions = await self.service.releases(TARGET.id, BUILD.package, BUILD.architecture)
        self.assertEqual(("10", "2"), versions.versions)
        new_service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(new_service.aclose)
        restored = await new_service.find(TARGET.id, BUILD, "all", "", 1, 10)
        self.assertEqual(("ready", False, 2), (restored.status, restored.refreshing, restored.total))
        self.assertEqual([1, 1], [len(item.fixes) for item in restored.items])
        self.assertEqual(1, self.source.calls)

    async def test_filter_counts_before_pagination_and_manual_unknown_version(self):
        await self.collect()
        page = await self.find(page=2, page_size=1)
        self.assertEqual((2, "CVE-2026-1002", 1, 1), (page.total, page.items[0].cve_id,
                                                       page.severity_counts["high"], page.severity_counts["low"]))
        filtered = await self.find(severity="low", search="TiMeR")
        self.assertEqual((1, 0, 1), (filtered.total, filtered.severity_counts["high"], filtered.severity_counts["low"]))
        missing = await self.find(version="999")
        self.assertEqual("partial", missing.status)
        self.assertIsNone(missing.total)
        self.assertTrue(missing.coverage_note)
        self.assertEqual(("ready", 0), ((await self.find(version="10")).status, (await self.find(version="10")).total))

    async def test_failed_refresh_retains_previous_data_and_backoff(self):
        before = self.now - timedelta(days=4)
        await self.seed(self.source.data, before)
        self.source.fail = True
        previous = await self.find()
        self.assertEqual(("stale", 2, True), (previous.status, previous.total, previous.refreshing))
        with self.assertLogs("src.application.services.daily_advisories", "WARNING"):
            await self.collect()
        failed = await self.find()
        self.assertEqual(("stale", 2, False), (failed.status, failed.total, failed.refreshing))
        self.assertEqual(before, failed.sources[0].refreshed_at)
        self.assertEqual(1, self.source.calls)
        self.assertTrue(failed.sources[0].note)
        new_service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(new_service.aclose)
        await new_service.refresh_scheduled()
        self.assertEqual(1, self.source.calls)
        reloaded = await new_service.find(TARGET.id, BUILD, "all", "", 1, 10)
        self.assertEqual(("stale", failed.sources[0].note), (reloaded.status, reloaded.sources[0].note))

    async def test_empty_source_failure_is_not_zero_and_incomplete_data_is_partial(self):
        self.source.fail = True
        with self.assertLogs("src.application.services.daily_advisories", "WARNING"):
            await self.collect()
        failed = await self.find()
        self.assertEqual(("error", None), (failed.status, failed.total))
        self.source.data = replace(self.source.data, complete=False, note="저장소 일부만 확인됨")
        self.now += timedelta(days=1)
        await self.seed(self.source.data, self.now)
        new_service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(new_service.aclose)
        partial = await new_service.find(TARGET.id, BUILD, "all", "", 1, 10)
        self.assertEqual(("partial", 2, self.source.data.note), (partial.status, partial.total, partial.sources[0].note))

    async def test_kst_daily_sync_without_visits_includes_new_cves_after_eight(self):
        self.source.release.set()
        await asyncio.gather(self.service.refresh_scheduled(), self.service.refresh_scheduled())
        self.assertEqual(1, self.source.calls)
        self.now += timedelta(minutes=1)
        await self.service.refresh_scheduled()
        self.assertEqual(1, self.source.calls)
        self.now += timedelta(minutes=1)
        self.source.data = replace(self.source.data, advisories=(*self.source.data.advisories, advisory("CVE-2026-1100", "9")))
        await self.service.refresh_scheduled()
        await self.service.refresh_scheduled()
        self.assertEqual(2, self.source.calls)
        self.assertEqual(("CVE-2026-1100",), tuple(item.cve_id for item in (await self.find(search="1100")).items))

    async def test_leases_are_transactional_and_expired_worker_cannot_overwrite(self):
        args = TARGET.id, FEED.id, scheduled_day(self.now)
        a, b = await asyncio.gather(
            self.store.claim(*args, "one", self.now), self.store.claim(*args, "two", self.now),
        )
        self.assertEqual(1, int(a.acquired) + int(b.acquired))
        old_owner = "one" if a.acquired else "two"
        self.now += timedelta(minutes=18)
        self.assertTrue((await self.store.claim(*args, "replacement", self.now)).acquired)
        self.assertFalse(await self.store.finish(TARGET.id, FEED.id, old_owner, None, "old error"))
        self.assertTrue(await self.store.finish(TARGET.id, FEED.id, "replacement", KernelSnapshot(self.source.data,self.now), None))
        self.assertIsNone((await self.store.load(TARGET.id, FEED.id)).error)

    async def test_hidden_upstream_feed_excludes_vendor_cves_for_any_arch_and_paginates(self):
        upstream_feed = replace(FEED, id="upstream")
        upstream = replace(TARGET, id="linux-upstream", feeds=(upstream_feed,))
        self.source.targets = (TARGET, upstream)
        source_data = KernelFeedData((
            advisory("CVE-2026-1003", "9", title="Known on another architecture"),
            advisory("CVE-2026-1100", "9", title="Kernel issue", issued_at="2026-10-01"),
            advisory("CVE-2026-1200", "9", title="New kernel issue", issued_at="2026-11-06"),
        ), ())
        await self.store.claim(upstream.id, upstream_feed.id, scheduled_day(self.now), "seed", self.now)
        await self.store.finish(upstream.id, upstream_feed.id, "seed", KernelSnapshot(source_data, self.now), None)
        await self.seed(self.source.data, self.now)
        service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        self.assertEqual((TARGET,), service.targets)
        page = await service.upstream(TARGET.id, "kernel", 1, 1)
        self.assertEqual(("ready", 2, ["CVE-2026-1200"]), (page.status, page.total, [x.cve_id for x in page.items]))

    async def test_architecture_without_its_source_is_unknown(self):
        arm = replace(FEED, id="arm", architectures=("aarch64",))
        x86 = replace(FEED, architectures=("x86_64",))
        target = replace(TARGET, architectures=("x86_64","aarch64"), feeds=(x86, arm))
        await self.seed(self.source.data, self.now)
        await self.store.claim(TARGET.id, arm.id, scheduled_day(self.now), "fixture", self.now)
        await self.store.finish(TARGET.id, arm.id, "fixture", None, "ARM source unavailable")
        self.source.targets = (target,)
        service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        missing = await service.find(TARGET.id, replace(BUILD, architecture="aarch64"), "all", "", 1, 10)
        self.assertEqual(("error", None, (), "arm"), (missing.status, missing.total, missing.items, missing.sources[0].id))
        self.assertTrue(missing.coverage_note)

    async def test_cached_responses_survive_network_fetch_and_snapshot_write(self):
        old_time = self.now - timedelta(days=1)
        await self.seed(self.source.data, old_time)
        upstream = replace(TARGET, id="linux-upstream", feeds=(replace(FEED, id="upstream"),))
        previous_upstream = KernelFeedData((advisory("CVE-2026-1100", "4", title="Previously unlinked"),), ())
        await self.store.claim(upstream.id, "upstream", scheduled_day(old_time), "seed", old_time)
        await self.store.finish(upstream.id, "upstream", "seed", KernelSnapshot(previous_upstream, old_time), None)
        self.source.targets = (TARGET, upstream)
        writing, finish = asyncio.Event(), asyncio.Event()
        write_snapshot = self.store.finish

        async def delayed_write(target, feed, owner, snapshot, error):
            if target == TARGET.id:
                writing.set()
                await finish.wait()
            return await write_snapshot(target, feed, owner, snapshot, error)

        async def updated_data(target, feed):
            if target == upstream:
                return previous_upstream
            self.source.started.set()
            await self.source.release.wait()
            return replace(self.source.data, builds=(*self.source.data.builds, replace(BUILD, version="3")),
                           advisories=(*self.source.data.advisories, advisory("CVE-2026-1100", "9")))

        async def read_all():
            return await asyncio.wait_for(asyncio.gather(service.releases(TARGET.id, BUILD.package, BUILD.architecture),
                service.find(TARGET.id, BUILD, "all", "", 1, 10), service.upstream(TARGET.id, "", 1, 10)), 2)

        self.store.finish = delayed_write
        self.source.fetch = updated_data
        service = KernelCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        refresh = asyncio.create_task(service.refresh_scheduled())
        try:
            await asyncio.wait_for(self.source.started.wait(), 2)
            for stage in ("fetch", "save"):
                if stage == "save":
                    self.source.release.set()
                    await asyncio.wait_for(writing.wait(), 2)
                versions, matches, unlinked = await read_all()
                self.assertTrue(all(result.refreshing for result in (versions, matches, unlinked)))
                self.assertEqual((("10", "2"), 2, 1), (versions.versions, matches.total, unlinked.total))
        finally:
            finish.set()
            self.source.release.set()
            await refresh
        versions, matches, unlinked = await read_all()
        self.assertEqual((("10", "3", "2"), 3, 0), (versions.versions, matches.total, unlinked.total))

    def test_scheduler_runs_at_startup_and_eight_kst(self):
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_kernel_cves=callback)
        job = scheduler.get_job("kernel_cves_daily")
        self.assertIs(job.func, callback)
        self.assertIsNotNone(job.next_run_time)
        self.assertEqual(datetime(2026, 11, 5, 23, tzinfo=timezone.utc), job.trigger.get_next_fire_time(None, self.now))

    async def test_protected_api_validates_selection_before_sync(self):
        auth = SimpleNamespace(enabled=True, resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="reader")))
        app = FastAPI()
        app.include_router(router)
        app.state.services = SimpleNamespace(auth=auth, kernel_cves=self.service)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.test") as client:
            base = "/api/v1/kernel-cves"
            params = dict(target=TARGET.id, package=BUILD.package, architecture=BUILD.architecture, version=BUILD.version)
            self.assertEqual(401, (await client.get(base, params=params)).status_code)
            client.headers["Authorization"] = "Bearer valid"
            options = (await client.get(base+"/targets")).json()["targets"]
            self.assertTrue(options[0]["available"])
            self.assertFalse(options[1]["available"])
            for changes in ({"version": "../file"}, {"target": "unavailable"}, {"package": "custom"}, {"page_size": 101}):
                self.assertEqual(422, (await client.get(base, params={**params, **changes})).status_code)
            self.assertEqual(0, self.source.calls)
            pending = await client.get(base, params=params)
            self.assertEqual(200, pending.status_code)
            self.assertIsNone(pending.json()["total"])
            self.assertEqual("no-store", pending.headers["cache-control"])
            await self.collect()
            response = await client.get(base, params=params)
            self.assertEqual(2, response.json()["total"])
            self.assertEqual("ERR-4", response.json()["items"][0]["fixes"][0]["advisory_id"])
