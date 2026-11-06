# backend/tests/test_database_cves.py
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

from src.application.use_cases.database_cves import DatabaseCveUseCase
from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeed, DatabaseFeedData, DatabaseTarget
from src.infrastructure.persistence.database_cve_store import SqliteDatabaseSnapshotStore
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.v1.router import router


RISK = DatabaseFeed("risk", "Vendor", "https://vendor.example/notices")
VERSIONS = DatabaseFeed("versions", "Releases", "https://vendor.example/releases", releases_only=True)
PRODUCTS = tuple(DatabaseTarget(key, name, (RISK, VERSIONS), "Official server releases")
                 for key, name in (("mariadb", "MariaDB"), ("mysql", "MySQL"), ("postgresql", "PostgreSQL")))
ROW = DatabaseAdvisory("CVE-2026-1000", "high", "notice-1", RISK.url, "2026-11-05", "10.6",
                       affected_from="10.6.9", affected_through="10.6.12", affected_through_inclusive=False,
                       component="Database server", cvss_score=7.5)


def version_key(value):
    return tuple(int(n) for n in value.split("."))


class Source:
    targets = PRODUCTS

    def __init__(self):
        self.records = (ROW, ROW, replace(ROW, cve_id="CVE-2026-1001", severity="medium", advisory_id="other"))
        self.fail = False
        self.calls = []

    async def fetch(self, target, feed):
        self.calls.append((target.id, feed.id))
        if feed.releases_only:
            return DatabaseFeedData((), (DatabaseBuild("10.6.10", "10.6", supported=False), DatabaseBuild("10.6.12", "10.6")))
        if self.fail:
            raise ValueError("fixture failure")
        return DatabaseFeedData(self.records, (DatabaseBuild("10.6.10", "10.6", issued_at="2026-11-05"),))

    @staticmethod
    def validate(target, version):
        if len(version_key(version)) != 3:
            raise ValueError("Invalid version")

    @staticmethod
    def matcher(target, version, data):
        if not version.startswith("10.6."):
            return None
        key = version_key(version)
        return lambda row: version_key(row.affected_from) <= key < version_key(row.affected_through)

    @staticmethod
    def coverage_note(target, version, data):
        return None if version.startswith("10.6.") else "미확인 계열"

    @staticmethod
    def compare_versions(target, a, b):
        return (version_key(a) > version_key(b)) - (version_key(a) < version_key(b))


class DatabaseCveTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = SqliteDatabaseSnapshotStore(str(Path(temp.name)/"database.sqlite3"))
        self.source = Source()
        self.now = datetime(2026, 11, 5, 22, 59, tzinfo=timezone.utc)
        self.service = self.reopen()

    def reopen(self):
        service = DatabaseCveUseCase(self.source, self.store, lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        return service

    async def test_api_exposes_product_bounds_and_preserves_null_fixes(self):
        app = FastAPI()
        app.include_router(router)
        app.state.services = SimpleNamespace(db_cves=self.service, auth=SimpleNamespace(
            enabled=True, resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="reader"))))
        address = "/api/v1/db-cves"
        params = {"target":"mariadb", "version":"10.6.10"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://example.test") as client:
            self.assertEqual(401, (await client.get(address, params=params)).status_code)
            client.headers["Authorization"] = "Bearer ok"
            targets = (await client.get(address+"/targets")).json()["targets"]
            self.assertEqual(["mariadb","mysql","postgresql"], [item["id"] for item in targets])
            self.assertEqual(422, (await client.get(address, params={**params,"target":"unknown"})).status_code)
            self.assertEqual(422, (await client.get(address, params={**params,"version":"latest"})).status_code)
            self.assertFalse(self.source.calls)
            await self.service.refresh_scheduled()
            releases = (await client.get(address+"/releases", params={"target":"mariadb"})).json()["versions"]
            self.assertEqual([("10.6.12", None), ("10.6.10", False)], [(r["version"], r["supported"]) for r in releases])
            result = await client.get(address, params={**params, "page_size":1, "page":2})
            self.assertEqual("no-store", result.headers["cache-control"])
            data = result.json()
            self.assertEqual((2, "CVE-2026-1001", 1, 1), (data["total"], data["items"][0]["cve_id"],
                                                          data["severity_counts"]["high"], data["severity_counts"]["medium"]))
            evidence = data["items"][0]["fixes"][0]
            self.assertEqual(("10.6","10.6.9",True,"10.6.12",False,None),
                             tuple(evidence[k] for k in ("series","affected_from","affected_from_inclusive","affected_through",
                                                         "affected_through_inclusive","fixed_version")))
            filtered = (await client.get(address, params={**params,"search":"10.6.9","severity":"high"})).json()
            self.assertEqual((1, 1), (filtered["total"], len(filtered["items"][0]["fixes"])))
            self.assertEqual(0, (await client.get(address, params={**params,"version":"10.6.12"})).json()["total"])
            unknown = (await client.get(address, params={**params,"version":"98.1.1"})).json()
            self.assertEqual(("partial", None), (unknown["status"], unknown["total"]))

    async def test_failure_retains_daily_snapshot_across_restart_then_discovers_new_cve(self):
        await self.service.refresh_scheduled()
        self.now += timedelta(minutes=1)
        self.source.fail = True
        with self.assertLogs("src.application.services.daily_advisories", "WARNING"):
            await asyncio.gather(self.service.refresh_scheduled(), self.service.refresh_scheduled())
        previous = self.reopen()
        await previous.refresh_scheduled()
        stale = await previous.find("mysql","10.6.10","all","",1,25)
        self.assertEqual((2, False, "stale"), (stale.total, stale.refreshing, stale.sources[0].status))
        self.assertEqual(12,len(self.source.calls))
        self.now += timedelta(days=1)
        self.source.fail = False
        self.source.records += (replace(ROW, cve_id="CVE-2026-1002"),)
        await previous.refresh_scheduled()
        self.assertEqual(3, (await previous.find("mysql","10.6.10","all","",1,25)).total)

    def test_daily_schedule_is_wired_at_startup_and_eight_kst(self):
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_db_cves=callback)
        job = scheduler.get_job("db_cves_daily")
        self.assertIs(job.func, callback)
        self.assertIsNotNone(job.next_run_time)
        self.assertEqual(self.now + timedelta(minutes=1), job.trigger.get_next_fire_time(None, self.now))
