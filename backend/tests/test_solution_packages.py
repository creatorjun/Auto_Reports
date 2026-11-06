# backend/tests/test_solution_packages.py
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
import httpx

from src.application.use_cases.solution_advisories import SolutionAdvisories
from src.infrastructure.persistence.solution_cve_store import SqliteSolutionSnapshotStore
from src.infrastructure.persistence.solution_packages import read_solution_packages
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.v1.router import router


class SolutionPackagesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        inventory_dir = Path(directory.name)
        self.inventory = inventory_dir / "eyecloudxoar_4_0_r2.json"
        self.enterContext(patch("src.infrastructure.persistence.solution_packages._INVENTORY_DIR", inventory_dir))

    def test_optional_inventory_is_empty_until_provisioned(self):
        self.assertEqual((), read_solution_packages("eyeCloudXoar", "4.0_R2"))
        self.inventory.write_text("malformed", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            read_solution_packages("eyeCloudXoar", "4.0_R2")

    def test_scheduler_runs_at_startup_and_at_0800_seoul(self):
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_solution_cves=callback)
        job = scheduler.get_job("solution_cves_daily")
        self.assertIs(job.func, callback)
        self.assertIsNotNone(job.next_run_time)
        before = datetime(2026, 11, 6, 22, 59, tzinfo=timezone.utc)
        self.assertEqual(datetime(2026, 11, 6, 23, tzinfo=timezone.utc), job.trigger.get_next_fire_time(None, before))

    async def test_inventory_is_authenticated_and_scoped_to_the_selected_release(self):
        base = {"name": "example", "version": "test", "category": "test", "evidence": "fixture"}
        rows = [
            {**base, "id": "sample-a", "cve_ids": ["CVE-2099-0001"]},
            {**base, "id": "sample-b", "cve_ids": []},
            {**base, "id": "sample-c", "cve_ids": None},
            {**base, "id": "sample-legacy"},
        ]
        self.inventory.write_text(json.dumps(rows), encoding="utf-8")
        app = FastAPI()
        app.include_router(router)
        service = SolutionAdvisories(read_solution_packages, AsyncMock(return_value={}),
                                     SqliteSolutionSnapshotStore(str(self.inventory.with_suffix(".sqlite3"))))
        self.addAsyncCleanup(service.aclose)
        app.state.services = SimpleNamespace(
            auth=SimpleNamespace(
                enabled=True, resolve_access_identity=AsyncMock(return_value=SimpleNamespace(username="reader")),
            ),
            solution_cves=service,
        )
        url = "/api/v1/solution-packages"
        release = {"product": "eyeCloudXoar", "version": "4.0_R2"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            self.assertEqual(401, (await client.get(url, params=release)).status_code)
            client.headers["Authorization"] = "Bearer ok"
            response = await client.get(url, params=release)
            self.assertEqual(200, response.status_code)
            self.assertEqual("no-store", response.headers["cache-control"])
            packages = response.json()["packages"]
            self.assertEqual([{"cve_ids": None, "cve_basis": "inventory", **row} for row in rows], packages)
            self.assertIn("coverage", response.json())
            for product, version in (
                ("eyeCloudXoar", "4.0_R1"), ("eyeCloudXoar", "4.0_R3"),
                ("eyeCloudSIM", "3.1.0"), ("eyeCloudSIM", "3.1.03"), ("eyeCloudAI", None),
            ):
                with self.subTest(product=product, version=version):
                    params = {"product": product}
                    if version is not None:
                        params["version"] = version
                    self.assertEqual({"packages": [], "coverage": None}, (await client.get(url, params=params)).json())
            for params in (
                {"product": "eyeCloudXoar"}, {"product": "eyeCloudSIM", "version": "4.0_R2"},
                {"product": "eyeCloudAI", "version": "4.0_R2"}, {"product": "unknown"},
            ):
                with self.subTest(params=params):
                    self.assertEqual(422, (await client.get(url, params=params)).status_code)
