# backend/src/application/use_cases/site_use_cases.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.domain.entities.site import Site
from src.domain.repositories.site_repository import SiteRepository


@dataclass
class SiteSummaryDTO:
    id: str
    site_name: str
    customer_name: str
    status: str
    contract_end_date: date


class SiteUseCase:
    def __init__(self, repository: SiteRepository) -> None:
        self._repo = repository

    async def get_all(self) -> list[Site]:
        return await self._repo.get_all()

    async def get_by_id(self, site_id: str) -> Optional[Site]:
        return await self._repo.get_by_id(site_id)

    async def create(self, site: Site) -> Site:
        existing = await self._repo.get_by_id(site.id)
        if existing:
            raise ValueError(f"Site '{site.id}' already exists")
        return await self._repo.save(site)

    async def update(self, site: Site) -> Site:
        existing = await self._repo.get_by_id(site.id)
        if not existing:
            raise ValueError(f"Site '{site.id}' not found")
        return await self._repo.save(site)

    async def delete(self, site_id: str) -> bool:
        return await self._repo.delete(site_id)

    async def search(self, query: str, limit: int = 10) -> list[SiteSummaryDTO]:
        sites = await self._repo.search(query, limit)
        return [self._to_summary_dto(s) for s in sites]

    async def get_recent(self, limit: int = 5) -> list[SiteSummaryDTO]:
        sites = await self._repo.get_recent(limit)
        return [self._to_summary_dto(s) for s in sites]

    def _to_summary_dto(self, site: Site) -> SiteSummaryDTO:
        return SiteSummaryDTO(
            id=site.id,
            site_name=site.site_name,
            customer_name=site.customer_info.name,
            status=site.status.value,
            contract_end_date=site.contract_end_date,
        )
