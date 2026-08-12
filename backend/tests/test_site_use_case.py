# backend/tests/test_site_use_case.py
import dataclasses
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.errors import EntityNotFoundError
from src.application.ports.site_repository import SiteRepository
from src.application.use_cases.site_use_cases import SiteUseCase
from src.domain.entities.site import DeploymentNode, Site


class InMemorySiteRepository(SiteRepository):
    def __init__(self, site: Site) -> None:
        self.site = site

    async def save(self, site: Site) -> Site:
        self.site = site
        return site

    async def find_by_id(self, site_id: int) -> Site | None:
        return self.site if self.site.id == site_id else None

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]:
        return [self.site]

    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]:
        return [self.site]

    async def update(self, site: Site) -> Site:
        return await self.save(site)

    async def delete(self, site_id: int) -> bool:
        return self.site.id == site_id

    async def count_all(self) -> int:
        return 1

    async def get_all(self) -> list[Site]:
        return [self.site]

    async def get_by_id(self, site_id: int) -> Site | None:
        return await self.find_by_id(site_id)

    async def search(self, query: str, limit: int = 10) -> list[Site]:
        return [self.site]

    async def get_recent(self, limit: int = 5) -> list[Site]:
        return [self.site]

    async def find_by_name(self, site_name: str) -> Site | None:
        return self.site if self.site.site_name == site_name else None


class SiteUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        site = Site(
            id=1,
            site_name="Alpha",
            nodes=[DeploymentNode(id=10, hostname="old")],
        )
        self.repository = InMemorySiteRepository(site)
        self.use_case = SiteUseCase(self.repository)

    async def test_updates_frozen_child_by_replacement(self) -> None:
        original = self.repository.site.nodes[0]
        updated = await self.use_case.update_node(1, 10, {"hostname": "new"})
        self.assertEqual("old", original.hostname)
        self.assertEqual("new", updated.nodes[0].hostname)
        self.assertIsNot(original, updated.nodes[0])

    async def test_missing_child_raises_application_error(self) -> None:
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.update_node(1, 999, {"hostname": "new"})
