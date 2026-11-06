# backend/tests/test_java_cves.py
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

from src.application.use_cases.java_cves import JavaCveUseCase
from src.domain.entities.java_cve import JavaAdvisory, JavaBuild, JavaFeed, JavaFeedData, JavaTarget
from src.infrastructure.persistence.java_cve_store import SqliteJavaSnapshotStore
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.v1.router import router


RISK = JavaFeed("risk", "Security notice", "https://example.test/notices")
BUILDS = JavaFeed("releases", "Release catalog", "https://example.test/builds", releases_only=True)
TARGET = JavaTarget("openjdk", "OpenJDK", (RISK, BUILDS), "Supplier advisories")
BUILD = JavaBuild("17.0.1", 17)


def record(cve, severity="high", **fields):
    return replace(JavaAdvisory(cve, severity, "notice", RISK.url, "2026-11-01", 17, affected_through="17.0.1",
                                component="Networking", cvss_score=7.4), **fields)


class JavaSource:
    targets = (TARGET,)

    def __init__(self):
        self.calls = []
        self.block = asyncio.Event()
        self.block.set()
        self.started = asyncio.Event()
        self.fail = False
        self.rows = (record("CVE-2026-1001"), record("CVE-2026-1001"), record("CVE-2026-1002", "low", component="XML"))

    async def fetch(self, target, feed):
        self.calls.append(feed.id)
        if feed.releases_only:
            return JavaFeedData((), (BUILD, JavaBuild("17.0.2", 17, "Java 17.0.2")))
        self.started.set()
        await self.block.wait()
        if self.fail:
            raise ValueError("unavailable")
        return JavaFeedData(self.rows, (BUILD,))

    @staticmethod
    def validate(target, version):
        if "/" in version:
            raise ValueError("Invalid Java build")

    @staticmethod
    def matcher(target, version, data):
        if version.startswith("99"):
            return None
        return lambda row: row.affected_through == version

    @staticmethod
    def coverage_note(target, version, data):
        return "공급사 권고 미확인" if version.startswith("99") else None

    @staticmethod
    def compare_versions(target, a, b):
        return (a > b) - (a < b)


class JavaCveTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.now = datetime(2026, 11, 5, 22, 59, tzinfo=timezone.utc)
        self.store = SqliteJavaSnapshotStore(str(Path(directory.name) / "java.sqlite3"))
        self.source = JavaSource()
        self.service = self.new_service()

    def new_service(self):
        service = JavaCveUseCase(self.source, self.store, clock=lambda: self.now)
        self.addAsyncCleanup(service.aclose)
        return service

    async def test_authenticated_api_preserves_evidence_and_filters_before_pagination(self):
        app = FastAPI()
        app.include_router(router)
        auth = SimpleNamespace(enabled=True, resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="reader")))
        app.state.services = SimpleNamespace(auth=auth, java_cves=self.service)
        backend = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=backend, base_url="https://example.test") as client:
            url = "/api/v1/java-cves"
            params = {"target":"openjdk", "version":"17.0.1"}
            self.assertEqual(401, (await client.get(url, params=params)).status_code)
            self.assertEqual(401, (await client.get(url+"/targets")).status_code)
            client.headers["Authorization"] = "Bearer ok"
            self.assertEqual("openjdk", (await client.get(url+"/targets")).json()["targets"][0]["id"])
            for changed in ({"target":"unknown"}, {"version":"../"}, {"severity":"incorrect"}, {"page_size":101}):
                self.assertEqual(422, (await client.get(url, params={**params, **changed})).status_code)
            self.assertFalse(self.source.calls)
            await self.service.refresh_scheduled()
            releases = await client.get(url+"/releases", params={"target":"openjdk"})
            self.assertEqual(["17.0.2","17.0.1"], [item["version"] for item in releases.json()["versions"]])
            self.assertEqual("17.0.1", releases.json()["versions"][1]["label"])
            result = await client.get(url, params={**params, "page":1, "page_size":1})
            self.assertEqual("no-store", result.headers["cache-control"])
            data = result.json()
            self.assertEqual(("ready", 2, 1, 1), (data["status"], data["total"], len(data["items"]), data["severity_counts"]["low"]))
            self.assertEqual(1, len(data["items"][0]["fixes"]))
            evidence = data["items"][0]["fixes"][0]
            self.assertEqual(("17.0.1", None, "Networking", 7.4), (evidence["affected_through"], evidence["fixed_version"],
                                                                  evidence["component"], evidence["cvss_score"]))
            filtered = (await client.get(url, params={**params,"search":"xMl","severity":"low"})).json()
            self.assertEqual((1, "CVE-2026-1002", 0), (filtered["total"], filtered["items"][0]["cve_id"], filtered["severity_counts"]["high"]))
            unknown = (await client.get(url, params={**params, "version":"99.1"})).json()
            self.assertEqual(("partial", None), (unknown["status"], unknown["total"]))
            clear = (await client.get(url, params={**params, "version":"17.0.2"})).json()
            self.assertEqual(("ready", 0), (clear["status"], clear["total"]))

    async def test_catalog_success_and_missing_advisories_cannot_report_zero(self):
        self.source.block.clear()
        pending = await self.service.find("openjdk","17.0.1","all","",1,1)
        self.assertEqual(("pending", None), (pending.status, pending.total))
        self.source.fail = True
        self.source.block.set()
        with self.assertLogs("src.application.services.daily_advisories", "WARNING"):
            await self.service.refresh_scheduled()
        results = await self.service.find("openjdk","17.0.1","all","",1,1)
        self.assertEqual(("error", None, False), (results.status, results.total, results.refreshing))
        self.assertEqual("17.0.2", (await self.service.releases("openjdk")).versions[0].version)

    async def test_daily_refresh_serves_previous_during_fetch_and_restores_without_refetch(self):
        await self.service.refresh_scheduled()
        self.assertEqual(["risk","releases"], self.source.calls)
        self.now += timedelta(minutes=1)
        self.source.rows += (record("CVE-2026-1003"),)
        self.source.block.clear()
        self.source.started.clear()
        task = asyncio.create_task(self.service.refresh_scheduled())
        await asyncio.wait_for(self.source.started.wait(),2)
        old = await asyncio.wait_for(self.service.find("openjdk","17.0.1","all","",1,25),2)
        self.assertEqual((2, True), (old.total, old.refreshing))
        self.source.block.set()
        await task
        latest = await self.service.find("openjdk","17.0.1","all","",1,25)
        self.assertEqual((3, False), (latest.total, latest.refreshing))
        restored = self.new_service()
        await restored.refresh_scheduled()
        other = await restored.find("openjdk","17.0.1","all","",1,25)
        self.assertEqual(latest, other)
        self.assertEqual(4, len(self.source.calls))

    def test_startup_and_daily_trigger_use_kst_even_if_reports_use_utc(self):
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_java_cves=callback)
        job = scheduler.get_job("java_cves_daily")
        self.assertIs(job.func, callback)
        self.assertIsNotNone(job.next_run_time)
        self.assertEqual(self.now + timedelta(minutes=1), job.trigger.get_next_fire_time(None,self.now))
