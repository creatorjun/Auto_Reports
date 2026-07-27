# backend/src/application/use_cases/site_use_cases.py
from typing import Optional

from src.domain.entities.site import Site
from src.domain.repositories.site_repository import SiteRepository


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
