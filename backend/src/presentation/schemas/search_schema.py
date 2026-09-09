# backend/src/presentation/schemas/search_schema.py
from pydantic import BaseModel

from src.domain.entities.search import SearchResult


class SearchResultSchema(BaseModel):
    type: str
    key: str
    title: str
    status: str
    issue_type: str
    url: str

    @classmethod
    def from_domain(cls, result: SearchResult) -> "SearchResultSchema":
        return cls(
            type=result.source.value,
            key=result.key,
            title=result.title,
            status=result.status,
            issue_type=result.item_type,
            url=result.url,
        )
