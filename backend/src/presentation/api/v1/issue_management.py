# backend/src/presentation/api/v1/issue_management.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.application.use_cases.issue_management import IssueManagementUseCase
from src.presentation.api.deps import ApiServices, get_api_services
from src.presentation.schemas.sla_dashboard_schema import SlaDashboardCommentPageSchema, SlaDashboardDescriptionSchema

router = APIRouter(prefix="/issue-management", tags=["issue-management"])


def get_issue_management(services: ApiServices = Depends(get_api_services)) -> IssueManagementUseCase:
    if services.issue_management is None:
        raise HTTPException(status_code=503, detail="Issue management is unavailable")
    return services.issue_management


@router.get("/issues")
async def list_issues(response: Response, use_case: IssueManagementUseCase = Depends(get_issue_management)):
    response.headers["Cache-Control"] = "no-store"
    return await use_case.list_issues()


@router.get("/issues/{issue_key}/description", response_model=SlaDashboardDescriptionSchema)
async def get_issue_description(issue_key: str, use_case: IssueManagementUseCase = Depends(get_issue_management)):
    try:
        return await use_case.get_issue_description(issue_key)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Jira 본문을 불러오지 못했습니다.") from error


@router.get("/issues/{issue_key}/description/images/{attachment_id}", response_class=Response)
async def get_description_image(issue_key: str, attachment_id: str, use_case: IssueManagementUseCase = Depends(get_issue_management)):
    try:
        image = await use_case.get_description_image(issue_key, attachment_id)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Jira 본문 이미지를 불러오지 못했습니다.") from error
    return Response(content=image.data, media_type=image.media_type, headers={"Cache-Control": "private, max-age=120"})


@router.get("/issues/{issue_key}/comments", response_model=SlaDashboardCommentPageSchema)
async def list_recent_comments(
    issue_key: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=5, ge=1),
    use_case: IssueManagementUseCase = Depends(get_issue_management),
):
    try:
        return await use_case.list_recent_comments(issue_key, offset=offset, limit=limit)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Jira 댓글을 불러오지 못했습니다.") from error


@router.get("/issues/{issue_key}/comments/{comment_id}/images/{attachment_id}", response_class=Response)
async def get_comment_image(
    issue_key: str,
    comment_id: str,
    attachment_id: str,
    use_case: IssueManagementUseCase = Depends(get_issue_management),
):
    try:
        image = await use_case.get_comment_image(issue_key, comment_id, attachment_id)
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Jira 댓글 이미지를 불러오지 못했습니다.") from error
    return Response(content=image.data, media_type=image.media_type, headers={"Cache-Control": "private, max-age=120"})
