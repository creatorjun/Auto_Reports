# backend/src/presentation/api/v1/search.py
from fastapi import APIRouter, Depends, Query

from src.application.use_cases.search import SearchUseCase
from src.presentation.api.deps import get_search_use_case
from src.presentation.schemas.search_schema import SearchResultSchema

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResultSchema])
async def search_jira_confluence(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
    use_case: SearchUseCase = Depends(get_search_use_case),
) -> list[SearchResultSchema]:
    results = await use_case.execute(query=q, limit=limit)
    return [SearchResultSchema.from_domain(result) for result in results]
