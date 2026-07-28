# backend/src/domain/repositories/site_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.site import Site


class SiteRepository(ABC):
    @abstractmethod
    async def save(self, site: Site) -> Site: ...

    @abstractmethod
    async def find_by_id(self, site_id: str) -> Optional[Site]: ...

    @abstractmethod
    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]: ...

    @abstractmethod
    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]: ...

    @abstractmethod
    async def update(self, site: Site) -> Site: ...

    @abstractmethod
    async def delete(self, site_id: str) -> bool: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def get_all(self) -> list[Site]: ...

    @abstractmethod
    async def get_by_id(self, site_id: str) -> Optional[Site]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[Site]: ...

    @abstractmethod
    async def get_recent(self, limit: int = 5) -> list[Site]: ...

    @abstractmethod
    async def find_by_name(self, site_name: str) -> Optional[Site]: ...
