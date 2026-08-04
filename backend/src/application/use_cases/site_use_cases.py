# backend/src/application/use_cases/site_use_cases.py
from src.domain.entities.site import DeploymentNode, PatchHistory, Site, VisitHistory
from src.domain.repositories.site_repository import SiteRepository


class SiteUseCase:
    def __init__(self, repository: SiteRepository) -> None:
        self._repo = repository

    async def get_all(self) -> list[Site]:
        return await self._repo.get_all()

    async def get_by_id(self, site_id: int) -> Site | None:
        return await self._repo.get_by_id(site_id)

    async def create(self, site: Site) -> Site:
        return await self._repo.save(site)

    async def update(self, site: Site) -> Site:
        return await self._repo.save(site)

    async def delete(self, site_id: int) -> bool:
        return await self._repo.delete(site_id)

    async def search(self, query: str, limit: int = 10) -> list[Site]:
        return await self._repo.search(query, limit)

    async def get_recent(self, limit: int = 5) -> list[Site]:
        return await self._repo.get_recent(limit)

    async def add_node(self, site_id: int, node: DeploymentNode) -> Site:
        site = await self._repo.get_by_id(site_id)
        if site is None:
            raise ValueError(f"Site not found: {site_id}")
        site.nodes.append(node)
        saved = await self._repo.save(site)
        refreshed = await self._repo.get_by_id(saved.id)
        return refreshed

    async def add_patch_history(self, site_id: int, ph: PatchHistory) -> Site:
        site = await self._repo.get_by_id(site_id)
        if site is None:
            raise ValueError(f"Site not found: {site_id}")
        site.patch_histories.append(ph)
        saved = await self._repo.save(site)
        refreshed = await self._repo.get_by_id(saved.id)
        return refreshed

    async def add_visit_history(self, site_id: int, vh: VisitHistory) -> Site:
        site = await self._repo.get_by_id(site_id)
        if site is None:
            raise ValueError(f"Site not found: {site_id}")
        site.visit_histories.append(vh)
        saved = await self._repo.save(site)
        refreshed = await self._repo.get_by_id(saved.id)
        return refreshed
