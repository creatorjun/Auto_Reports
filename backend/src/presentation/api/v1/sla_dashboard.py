# backend/src/presentation/api/v1/sla_dashboard.py
from fastapi import APIRouter, Depends, HTTPException, Response

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


@router.get(
    "/issues/{issue_key}/comments/{comment_id}/images/{attachment_id}",
    response_class=Response,
)
async def get_comment_image(
    issue_key: str,
    comment_id: str,
    attachment_id: str,
    use_case: SlaDashboardUseCase = Depends(get_sla_dashboard_use_case),
):
    try:
        image = await use_case.get_comment_image(
            issue_key,
            comment_id,
            attachment_id,
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail="Jira 댓글 이미지를 불러오지 못했습니다.",
        ) from error
    return Response(
        content=image.data,
        media_type=image.media_type,
        headers={"Cache-Control": "private, max-age=120"},
    )
