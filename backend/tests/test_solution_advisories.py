# backend/tests/test_solution_advisories.py
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock

from src.application.use_cases.solution_advisories import SolutionAdvisories
from src.domain.entities.solution_package import SolutionPackage
from src.infrastructure.persistence.solution_cve_store import SqliteSolutionSnapshotStore


RELEASE = ("eyeCloudXoar", "4.0_R2")
INVENTORY = (
    SolutionPackage("a", "example:lib", "1.0", "Java", "fixture", ("CVE-2099-0001",)),
    SolutionPackage("b", "example:other", "1.0", "Java", "fixture", ("CVE-2099-0002",)),
    SolutionPackage("c", "example-js", "2.0", "web", "fixture"),
    SolutionPackage("d", "example-addon", "2.0", "web", "fixture", ("CVE-2099-0004",)),
    SolutionPackage("e", "example server", "3.0", "server", "fixture"),
)


class SolutionAdvisoriesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = str(Path(directory.name) / "snapshots.sqlite3")
        self.packages = INVENTORY
        self.now = datetime(2026, 11, 6, 22, 59, tzinfo=timezone.utc)
        self.by_feed = {
            "Maven": {"a": ("CVE-2099-1001",), "b": ()},
            "npm": {"c": ("CVE-2099-1002",), "d": None},
        }
        self.match = AsyncMock(side_effect=self.fetch)
        self.service = self.open_service()

    def read_inventory(self, product, version):
        if (product, version) == RELEASE:
            return self.packages
        return () if (product, version) == ("eyeCloudAI", None) else None

    async def fetch(self, packages, ecosystem):
        result = self.by_feed[ecosystem]
        if isinstance(result, Exception):
            raise result
        return result

    def open_service(self):
        service = SolutionAdvisories(self.read_inventory, self.match, SqliteSolutionSnapshotStore(self.path),
                                     lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        return service

    async def test_empty_and_unregistered_selections_never_start_a_request(self):
        self.packages = ()
        await self.service.refresh_scheduled()
        self.assertIsNone((await self.service.get(*RELEASE)).coverage)
        self.assertEqual((), (await self.service.get("eyeCloudAI", None)).packages)
        self.assertIsNone(await self.service.get("unknown", None))
        self.assertFalse(Path(self.path).exists())
        self.match.assert_not_awaited()

    async def test_merge_preserves_unknown_and_replaces_confirmed_zero(self):
        first = await self.service.get(*RELEASE)
        self.assertEqual(INVENTORY, first.packages)
        await asyncio.gather(self.service.refresh_scheduled(), self.service.refresh_scheduled())
        self.assertEqual(2, self.match.await_count)
        result = await self.service.get(*RELEASE)
        self.assertEqual(
            [("advisory", ("CVE-2099-1001",)), ("advisory", ()), ("advisory", ("CVE-2099-1002",)),
             ("inventory", ("CVE-2099-0004",)), ("inventory", None)],
            [(p.cve_basis, p.cve_ids) for p in result.packages],
        )
        self.assertIn("OSV 권고 대조 3개", result.coverage.coverage_note)
        restored = await self.open_service().get(*RELEASE)
        self.assertEqual(result, restored)
        self.assertEqual(2, self.match.await_count)

    async def test_refresh_and_failure_preserve_last_confirmed_rows_of_the_same_inventory(self):
        await self.service.refresh_scheduled()
        previous = await self.service.get(*RELEASE)
        self.now += timedelta(minutes=1)
        self.by_feed["Maven"] = ValueError("test failure")
        self.by_feed["npm"] = {"c": (), "d": None}
        with self.assertLogs("src.application.services.daily_advisories", level="WARNING"):
            during = await self.service.get(*RELEASE)
            self.assertTrue(during.coverage.refreshing)
            self.assertEqual(previous.packages, during.packages)
            await self.service.refresh_scheduled()
        result = await self.service.get(*RELEASE)
        self.assertEqual("partial", result.coverage.status)
        self.assertEqual("stale", next(source.status for source in result.coverage.sources if source.id == "Maven"))
        self.assertEqual(previous.packages[:2], result.packages[:2])
        self.assertEqual(("advisory", ()), (result.packages[2].cve_basis, result.packages[2].cve_ids))
        restored = await self.open_service().get(*RELEASE)
        self.assertEqual(result, restored)

    async def test_reassigned_id_does_not_reuse_saved_matches_even_on_the_same_day(self):
        await self.service.refresh_scheduled()
        self.packages = (replace(INVENTORY[0], name="example:replacement", version="4.0", cve_ids=None),)
        self.by_feed = {"Maven": {"a": ()}, "npm": {}}
        fresh = await self.open_service().get(*RELEASE)
        self.assertEqual(self.packages, fresh.packages)
        await self.service.refresh_scheduled()
        result = await self.service.get(*RELEASE)
        self.assertEqual(("advisory", ()), (result.packages[0].cve_basis, result.packages[0].cve_ids))
        self.assertEqual(4, self.match.await_count)
