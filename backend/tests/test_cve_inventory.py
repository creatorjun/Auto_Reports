# backend/tests/test_cve_inventory.py
import asyncio
import tempfile
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

from src.application.use_cases.cve_inventory import CveInventoryUseCase, CveRefreshThrottled
from src.domain.entities.cve_inventory import CveFinding, CveInventory, CveInventoryPackage, CvePackageSnapshot, CveVersionRange
from src.infrastructure.persistence.cve_inventory_snapshot_store import SqliteCveInventorySnapshotStore


class CveInventoryUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 10, 28, tzinfo=timezone.utc)
        self.packages = (
            CveInventoryPackage("one", "example", "npm", ("1.0.0",)),
            CveInventoryPackage("two", "second", "Maven", ("2.0.0",)),
            CveInventoryPackage("three", "unmapped", "generic", ("unknown",), mapping_status="mapping_required"),
        )
        self.loader = AsyncMock()
        self.loader.load.return_value = CveInventory("dataset-one", "2026-10-22", self.packages, 3, 3)
        self.source = AsyncMock()
        self.source.begin_refresh.return_value = frozenset({"CVE-2020-12345"})
        self.source.fetch.side_effect = lambda value: (
            CveFinding("CVE-2020-12345", "Old package CVE", severity="critical", inventory_impact="not_affected"),
        ) if value.id == "one" else (CveFinding("CVE-2026-12346", "Unrated vulnerability"),)
        self.directory = tempfile.TemporaryDirectory()
        self.store = SqliteCveInventorySnapshotStore(str(Path(self.directory.name) / "snapshot.sqlite3"))
        self.service = CveInventoryUseCase(self.loader, self.source, self.store, clock=lambda: self.now)

    async def asyncTearDown(self):
        await self.service.aclose()
        await self.store.aclose()
        self.directory.cleanup()

    async def refresh(self):
        await self.service.get_snapshot(refresh=True)
        await self.service._task

    async def test_get_never_fetches_and_default_includes_all_versions_with_unknown_severity(self):
        result = await self.service.get_snapshot()
        self.source.fetch.assert_not_awaited()
        self.assertEqual(0, result["total"])
        self.assertEqual(1, result["coverage"]["unmapped"])
        await self.refresh()
        result = await self.service.get_snapshot()
        self.assertEqual(2, result["total"])
        self.assertEqual("not_affected", result["items"][0]["inventory_impact"])
        self.assertEqual(1, result["severity_counts"]["unknown"])
        self.assertEqual(2, result["coverage"]["ok"])
        selected = await self.service.get_snapshot(severity="unknown", page_size=1)
        self.assertEqual(1, selected["total"])
        self.assertEqual("CVE-2026-12346", selected["items"][0]["cve_id"])
        self.assertEqual(0, (await self.service.get_snapshot(impact="affected"))["total"])

    async def test_refresh_is_background_and_concurrent_requests_share_worker(self):
        entered = asyncio.Event()
        release = asyncio.Event()

        async def fetch(package):
            entered.set()
            await release.wait()
            return ()

        self.source.fetch.side_effect = fetch
        result = await self.service.get_snapshot(refresh=True)
        self.assertTrue(result["refreshing"])
        await entered.wait()
        task = self.service._task
        await self.service.get_snapshot(refresh=True)
        self.assertIs(task, self.service._task)
        release.set()
        await task
        self.assertEqual(2, self.source.fetch.await_count)

    async def test_failures_preserve_last_good_results_and_exploitation_flags(self):
        await self.refresh()
        original = (await self.service.get_snapshot())["items"][0]
        self.now += timedelta(hours=2)
        self.source.begin_refresh.return_value = None
        self.source.fetch.side_effect = RuntimeError("provider unavailable")
        await self.refresh()
        result = await self.service.get_snapshot()
        self.assertEqual(2, result["coverage"]["stale"])
        self.assertEqual(2, result["total"])
        self.assertTrue(result["items"][0]["known_exploited"])
        self.assertEqual(original["first_seen_at"], result["items"][0]["first_seen_at"])

    async def test_snapshot_restore_preserves_cooldown_and_first_seen(self):
        await self.refresh()
        original = await self.service.get_snapshot()
        restored = CveInventoryUseCase(self.loader, self.source, self.store, clock=lambda: self.now)
        try:
            value = await restored.get_snapshot()
            self.assertEqual(original["items"], value["items"])
            self.assertEqual(7200, value["retry_after_seconds"])
            with self.assertRaises(CveRefreshThrottled):
                await restored.get_snapshot(refresh=True)
        finally:
            await restored.aclose()

    async def test_restart_refreshes_overdue_cached_inventory_but_preserves_cooldown(self):
        await self.refresh()
        restored = CveInventoryUseCase(self.loader, self.source, self.store, clock=lambda: self.now)
        try:
            await restored.start_if_needed()
            self.assertIsNone(restored._task)
            self.assertEqual(2, self.source.fetch.await_count)
            self.now += timedelta(hours=2)
            await restored.start_if_needed()
            self.assertIsNotNone(restored._task)
            await restored._task
            self.assertEqual(4, self.source.fetch.await_count)
        finally:
            await restored.aclose()

    async def test_first_seen_survives_removal_and_reappearance(self):
        await self.refresh()
        original = (await self.service.get_snapshot())["items"][0]["first_seen_at"]
        self.now += timedelta(hours=2)
        self.source.fetch.side_effect = lambda package: ()
        await self.refresh()
        self.assertEqual(0, (await self.service.get_snapshot())["total"])
        self.now += timedelta(hours=2)
        self.source.fetch.side_effect = lambda package: (CveFinding("CVE-2020-12345", "Returned CVE"),)
        await self.refresh()
        rows = (await self.service.get_snapshot())["items"]
        self.assertEqual(original, next(row for row in rows if row["package_id"] == "one")["first_seen_at"])

    async def test_inventory_change_invalidates_snapshot_without_claiming_old_coverage(self):
        await self.refresh()
        self.loader.load.return_value = replace(self.loader.load.return_value, dataset_id="dataset-two")
        self.source.fetch.side_effect = lambda package: ()
        await self.refresh()
        result = await self.service.get_snapshot()
        self.assertEqual("dataset-two", result["inventory"]["dataset_id"])
        self.assertEqual(0, result["total"])
        self.assertEqual(2, result["coverage"]["ok"])

    async def test_package_coverage_filters_keep_unmapped_visible(self):
        await self.refresh()
        result = await self.service.get_packages(status="unmapped")
        self.assertEqual(1, result["total"])
        self.assertEqual("unmapped", result["items"][0]["name"])
        self.assertEqual(0, result["items"][0]["cve_count"])
        self.assertEqual("unmapped", result["items"][0]["status"])

    async def test_initial_background_collection_runs_once_and_cancellation_persists_attempt(self):
        entered = asyncio.Event()

        async def fetch(package):
            entered.set()
            await asyncio.Event().wait()

        self.source.fetch.side_effect = fetch
        await self.service.start_if_needed()
        await entered.wait()
        await self.service.aclose()
        saved = await self.store.load()
        self.assertIsNotNone(saved.last_attempt_at)
        self.assertFalse(saved.initialized)
        restored = CveInventoryUseCase(self.loader, self.source, self.store, clock=lambda: self.now)
        try:
            await restored.start_if_needed()
            self.assertIsNone(restored._task)
        finally:
            await restored.aclose()

    async def test_twenty_thousand_rows_filter_and_serialize_only_the_selected_page(self):
        await self.service.initialize()
        version_range = CveVersionRange("< 2.0.0", "2.0.0")
        findings = tuple(CveFinding(
            f"CVE-2026-{10000 + number}", "Package vulnerability", ranges=(version_range,),
            severity="high" if number % 2 else "unknown",
        ) for number in range(20201))
        self.service._states["one"] = CvePackageSnapshot("one", findings, "ok")
        started = time.perf_counter()
        result = await self.service.get_snapshot(severity="high", page=100, page_size=50)
        elapsed = time.perf_counter() - started
        self.assertEqual(10100, result["total"])
        self.assertEqual(50, len(result["items"]))
        self.assertEqual(10101, result["severity_counts"]["unknown"])
        self.assertLess(elapsed, 3)
        self.assertIs(version_range, self.service._rows[0]["ranges"][0])
        self.assertEqual({"affected": "< 2.0.0", "fixed": "2.0.0", "type": "ECOSYSTEM"}, result["items"][0]["ranges"][0])

    async def test_successful_refresh_keeps_kev_flags_when_supplemental_source_is_unavailable(self):
        await self.refresh()
        self.now += timedelta(hours=2)
        self.source.begin_refresh.return_value = None
        await self.refresh()
        self.assertTrue((await self.service.get_snapshot())["items"][0]["known_exploited"])

    async def test_scheduled_tick_jitter_does_not_skip_a_two_hour_cycle(self):
        await self.refresh()
        self.now += timedelta(hours=2, microseconds=-100)
        await self.service.refresh_scheduled()
        self.assertEqual(4, self.source.fetch.await_count)

    async def test_new_cve_in_existing_advisory_gets_its_own_first_seen(self):
        self.source.fetch.side_effect = lambda package: (CveFinding("CVE-2026-12345", "First CVE", source_ids=("ELSA-2026-1000",)),)
        await self.refresh()
        self.now += timedelta(hours=2)
        self.source.fetch.side_effect = lambda package: (
            CveFinding("CVE-2026-12345", "First CVE", source_ids=("ELSA-2026-1000",)),
            CveFinding("CVE-2026-12346", "New CVE", source_ids=("ELSA-2026-1000",)),
        )
        await self.refresh()
        result = await self.service.get_snapshot(search="CVE-2026-12346")
        self.assertTrue(all(row["first_seen_at"] == self.now.isoformat() for row in result["items"]))
