# backend/src/application/use_cases/search.py
from src.application.ports.search_port import SearchPort
from src.domain.entities.search import SearchResult


class SearchUseCase:
    def __init__(self, search: SearchPort) -> None:
        self._search = search

    async def execute(self, query: str, limit: int = 5) -> list[SearchResult]:
        return await self._search.search(query=query, limit=limit)
