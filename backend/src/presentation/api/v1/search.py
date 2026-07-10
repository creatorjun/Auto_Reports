# backend/src/presentation/api/v1/search.py
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.domain.ports.jira_port import JiraPort
from src.presentation.api.deps import get_jira

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[dict[str, Any]])
async def search_jira_confluence(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
    jira: JiraPort = Depends(get_jira),
) -> list[dict[str, Any]]:
    return await jira.search(query=q, limit=limit)
