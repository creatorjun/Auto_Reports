# backend/tests/test_search_use_case.py
import unittest

from src.application.use_cases.search import SearchUseCase
from src.domain.entities.search import SearchResult, SearchSource
from src.presentation.schemas.search_schema import SearchResultSchema


class SearchGateway:
    def __init__(self) -> None:
        self.request: tuple[str, int] | None = None

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        self.request = (query, limit)
        return [
            SearchResult(
                source=SearchSource.JIRA,
                key="TACEA-1",
                title="검색 결과",
                status="할 일",
                item_type="인시던트",
                url="https://jira.example.com/browse/TACEA-1",
            )
        ]


class SearchUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_uses_typed_result_and_preserves_http_contract(self) -> None:
        gateway = SearchGateway()

        results = await SearchUseCase(gateway).execute("검색어", 7)
        schema = SearchResultSchema.from_domain(results[0])

        self.assertEqual(("검색어", 7), gateway.request)
        self.assertEqual("jira", schema.type)
        self.assertEqual("인시던트", schema.issue_type)

    async def test_trims_outer_whitespace_and_preserves_word_spacing(self) -> None:
        gateway = SearchGateway()
        await SearchUseCase(gateway).execute(" \t서울 교통공사\n ", 7)
        self.assertEqual(("서울 교통공사", 7), gateway.request)

    async def test_whitespace_only_query_does_not_call_gateway(self) -> None:
        gateway = SearchGateway()
        self.assertEqual([], await SearchUseCase(gateway).execute(" \t\n "))
        self.assertIsNone(gateway.request)
