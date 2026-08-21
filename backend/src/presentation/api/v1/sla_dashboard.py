# backend/src/presentation/api/v1/sla_dashboard.py
from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.sla_dashboard import SlaDashboardUseCase
from src.presentation.api.v1.deps import get_sla_dashboard_use_case
from src.presentation.schemas.sla_dashboard_schema import (
    SlaDashboardCommentSchema,
    SlaDashboardIssueSchema,
)

router = APIRouter(prefix="/sla-dashboard", tags=["sla-dashboard"])


@router.get("/issues", response_model=list[SlaDashboardIssueSchema])
async def list_recent_issues(
    use_case: SlaDashboardUseCase = Depends(get_sla_dashboard_use_case),
):
    return await use_case.list_recent_issues()


@router.get(
    "/issues/{issue_key}/comments",
    response_model=list[SlaDashboardCommentSchema],
)
async def list_recent_comments(
    issue_key: str,
    use_case: SlaDashboardUseCase = Depends(get_sla_dashboard_use_case),
):
    try:
        return await use_case.list_recent_comments(issue_key)
    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail="Jira 댓글을 불러오지 못했습니다.",
        ) from error
