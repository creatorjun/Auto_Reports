# backend/src/application/use_cases/site_use_cases.py
from dataclasses import replace

from src.application.errors import EntityNotFoundError
from src.application.ports.site_repository import SiteRepository
from src.domain.entities.site import DeploymentNode, PatchHistory, Site, VisitHistory


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

    async def update_fields(self, site_id: int, changes: dict[str, object]) -> Site:
        site = await self._get_required(site_id)
        return await self._repo.save(replace(site, **changes))

    async def delete(self, site_id: int) -> bool:
        return await self._repo.delete(site_id)

    async def search(self, query: str, limit: int = 10) -> list[Site]:
        return await self._repo.search(query, limit)

    async def get_recent(self, limit: int = 5) -> list[Site]:
        return await self._repo.get_recent(limit)

    async def add_node(self, site_id: int, node: DeploymentNode) -> Site:
        site = await self._get_required(site_id)
        return await self._save_and_refresh(replace(site, nodes=[*site.nodes, node]))

    async def update_node(
        self,
        site_id: int,
        node_id: int,
        changes: dict[str, object],
    ) -> Site:
        site = await self._get_required(site_id)
        if not any(node.id == node_id for node in site.nodes):
            raise EntityNotFoundError("DeploymentNode", node_id)
        nodes = [
            replace(node, **changes) if node.id == node_id else node
            for node in site.nodes
        ]
        return await self._save_and_refresh(replace(site, nodes=nodes))

    async def delete_node(self, site_id: int, node_id: int) -> None:
        site = await self._get_required(site_id)
        nodes = [node for node in site.nodes if node.id != node_id]
        if len(nodes) == len(site.nodes):
            raise EntityNotFoundError("DeploymentNode", node_id)
        await self._repo.save(replace(site, nodes=nodes))

    async def add_patch_history(self, site_id: int, ph: PatchHistory) -> Site:
        site = await self._get_required(site_id)
        histories = [*site.patch_histories, ph]
        return await self._save_and_refresh(replace(site, patch_histories=histories))

    async def update_patch_history(
        self,
        site_id: int,
        history_id: int,
        changes: dict[str, object],
    ) -> Site:
        site = await self._get_required(site_id)
        if not any(item.id == history_id for item in site.patch_histories):
            raise EntityNotFoundError("PatchHistory", history_id)
        histories = [
            replace(item, **changes) if item.id == history_id else item
            for item in site.patch_histories
        ]
        return await self._save_and_refresh(replace(site, patch_histories=histories))

    async def delete_patch_history(self, site_id: int, history_id: int) -> None:
        site = await self._get_required(site_id)
        histories = [
            item for item in site.patch_histories if item.id != history_id
        ]
        if len(histories) == len(site.patch_histories):
            raise EntityNotFoundError("PatchHistory", history_id)
        await self._repo.save(replace(site, patch_histories=histories))

    async def add_visit_history(self, site_id: int, vh: VisitHistory) -> Site:
        site = await self._get_required(site_id)
        histories = [*site.visit_histories, vh]
        return await self._save_and_refresh(replace(site, visit_histories=histories))

    async def update_visit_history(
        self,
        site_id: int,
        history_id: int,
        changes: dict[str, object],
    ) -> Site:
        site = await self._get_required(site_id)
        if not any(item.id == history_id for item in site.visit_histories):
            raise EntityNotFoundError("VisitHistory", history_id)
        histories = [
            replace(item, **changes) if item.id == history_id else item
            for item in site.visit_histories
        ]
        return await self._save_and_refresh(replace(site, visit_histories=histories))

    async def delete_visit_history(self, site_id: int, history_id: int) -> None:
        site = await self._get_required(site_id)
        histories = [
            item for item in site.visit_histories if item.id != history_id
        ]
        if len(histories) == len(site.visit_histories):
            raise EntityNotFoundError("VisitHistory", history_id)
        await self._repo.save(replace(site, visit_histories=histories))

    async def _get_required(self, site_id: int) -> Site:
        site = await self._repo.get_by_id(site_id)
        if site is None:
            raise EntityNotFoundError("Site", site_id)
        return site

    async def _save_and_refresh(self, site: Site) -> Site:
        saved = await self._repo.save(site)
        if saved.id is None:
            raise RuntimeError("Saved site has no identifier")
        refreshed = await self._repo.get_by_id(saved.id)
        if refreshed is None:
            raise EntityNotFoundError("Site", saved.id)
        return refreshed
