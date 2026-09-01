# backend/tests/test_site_repository.py
import time
import unittest
from datetime import date
from types import SimpleNamespace

from src.domain.entities.site import DeploymentNode, PatchHistory, Site, SiteStatus, VisitHistory
from src.infrastructure.persistence.site_models import (
    DeploymentNodeORM,
    PatchHistoryORM,
    SiteORM,
    VisitHistoryORM,
)
from src.infrastructure.persistence.site_repository_impl import SiteRepositoryImpl


class FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows=()) -> None:
        self.rows = list(rows)
        self.statements = []
        self.deleted = []

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.rows)

    async def delete(self, value) -> None:
        self.deleted.append(value)

    def add(self, value) -> None:
        return None


class SiteRepositoryPerformanceTest(unittest.IsolatedAsyncioTestCase):
    async def test_summary_queries_select_only_summary_columns(self) -> None:
        row = SimpleNamespace(
            id=1,
            site_name="Alpha",
            customer_name="Kim",
            status="active",
            contract_end_date=date(2027, 1, 31),
        )
        session = FakeSession([row])
        repository = SiteRepositoryImpl(session)

        results = await repository.search("alpha", limit=10)

        self.assertEqual(1, len(session.statements))
        self.assertNotIn("deployment_nodes", str(session.statements[0]))
        self.assertEqual("Alpha", results[0].site_name)
        self.assertEqual("Kim", results[0].customer_name)
        self.assertEqual(SiteStatus.ACTIVE, results[0].status)

    async def test_child_reconciliation_scales_linearly(self) -> None:
        child_count = 3_000
        orm = SiteORM(site_name="Alpha")
        orm.nodes = [
            DeploymentNodeORM(id=index, hostname="old")
            for index in range(1, child_count + 1)
        ]
        orm.patch_histories = [
            PatchHistoryORM(id=index, note="old")
            for index in range(1, child_count + 1)
        ]
        orm.visit_histories = [
            VisitHistoryORM(id=index, engineer_name="old")
            for index in range(1, child_count + 1)
        ]
        site = Site(
            site_name="Alpha",
            nodes=[
                DeploymentNode(id=index, hostname="new")
                for index in range(1, child_count + 1)
            ],
            patch_histories=[
                PatchHistory(id=index, note="new")
                for index in range(1, child_count + 1)
            ],
            visit_histories=[
                VisitHistory(id=index, engineer_name="new")
                for index in range(1, child_count + 1)
            ],
        )
        session = FakeSession()
        repository = SiteRepositoryImpl(session)

        started = time.perf_counter()
        await repository._apply_domain(orm, site)
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0)
        self.assertEqual("new", orm.nodes[-1].hostname)
        self.assertEqual("new", orm.patch_histories[-1].note)
        self.assertEqual("new", orm.visit_histories[-1].engineer_name)
        self.assertEqual([], session.deleted)
