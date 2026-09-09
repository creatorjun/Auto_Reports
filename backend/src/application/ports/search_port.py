# backend/src/application/ports/search_port.py
from abc import ABC, abstractmethod

from src.domain.entities.search import SearchResult


class SearchPort(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]: ...
