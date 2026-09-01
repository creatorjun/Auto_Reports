# backend/src/application/ports/site_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.site import Site, SiteSummary


class SiteRepository(ABC):
    @abstractmethod
    async def save(self, site: Site) -> Site: ...

    @abstractmethod
    async def find_by_id(self, site_id: int) -> Optional[Site]: ...

    @abstractmethod
    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]: ...

    @abstractmethod
    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]: ...

    @abstractmethod
    async def update(self, site: Site) -> Site: ...

    @abstractmethod
    async def delete(self, site_id: int) -> bool: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def get_all(self) -> list[SiteSummary]: ...

    @abstractmethod
    async def get_by_id(self, site_id: int) -> Optional[Site]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SiteSummary]: ...

    @abstractmethod
    async def get_recent(self, limit: int = 5) -> list[SiteSummary]: ...

    @abstractmethod
    async def find_by_name(self, site_name: str) -> Optional[Site]: ...
