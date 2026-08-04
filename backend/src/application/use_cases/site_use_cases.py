# backend/src/application/use_cases/site_use_cases.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.domain.entities.site import DeploymentNode, PatchHistory, Site, VisitHistory
from src.domain.repositories.site_repository import SiteRepository


@dataclass
class SiteSummaryDTO:
    id: int
    site_name: str
    customer_name: Optional[str]
    status: Optional[str]
    contract_end_date: Optional[date]


class SiteUseCase:
    def __init__(self, repository: SiteRepository) -> None:
        self._repo = repository

    async def get_all(self) -> list[Site]:
        return await self._repo.get_all()

    async def get_by_id(self, site_id: int) -> Optional[Site]:
        return await self._repo.get_by_id(site_id)

    async def create(self, site: Site) -> Site:
        existing = await self._repo.find_by_name(site.site_name)
        if existing is not None:
            raise ValueError(f"이미 동일한 이름의 사이트가 존재합니다: '{site.site_name}'")
        return await self._repo.save(site)

    async def update(self, site: Site) -> Site:
        return await self._repo.save(site)

    async def delete(self, site_id: int) -> bool:
        return await self._repo.delete(site_id)

    async def search(self, query: str, limit: int = 10) -> list[SiteSummaryDTO]:
        sites = await self._repo.search(query, limit)
        return [self._to_summary_dto(s) for s in sites]

    async def get_recent(self, limit: int = 5) -> list[SiteSummaryDTO]:
        sites = await self._repo.get_recent(limit)
        return [self._to_summary_dto(s) for s in sites]

    async def add_node(self, site_id: int, node: DeploymentNode) -> Site:
        site = await self._repo.get_by_id(site_id)
        if not site:
            raise ValueError(f"Site '{site_id}' not found")
        site.nodes.append(node)
        return await self._repo.save(site)

    async def add_patch_history(self, site_id: int, patch: PatchHistory) -> Site:
        site = await self._repo.get_by_id(site_id)
        if not site:
            raise ValueError(f"Site '{site_id}' not found")
        site.patch_histories.append(patch)
        return await self._repo.save(site)

    async def add_visit_history(self, site_id: int, visit: VisitHistory) -> Site:
        site = await self._repo.get_by_id(site_id)
        if not site:
            raise ValueError(f"Site '{site_id}' not found")
        site.visit_histories.append(visit)
        return await self._repo.save(site)

    def _to_summary_dto(self, site: Site) -> SiteSummaryDTO:
        return SiteSummaryDTO(
            id=site.id,
            site_name=site.site_name,
            customer_name=site.customer_contact.name if site.customer_contact else None,
            status=site.status.value if site.status else None,
            contract_end_date=site.contract_end_date,
        )
