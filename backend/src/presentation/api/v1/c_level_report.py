# backend/src/presentation/api/v1/c_level_report.py
from collections.abc import AsyncIterator
from datetime import date as CalendarDate
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.application.errors import EntityNotFoundError
from src.application.ports.audit_port import AuditPort
from src.application.use_cases.c_level_workspace import CLevelPreviewExpiredError, CLevelWorkspaceUseCase
from src.domain.entities.c_level_history import CLevelComment, CLevelSnapshotSummary
from src.presentation.api.deps import ApiServices, get_api_services, get_audit
from src.presentation.api.v1.deps import require_auth
from src.presentation.http.client_ip import get_client_ip
from src.presentation.schemas.c_level_schema import CLevelCommentRequest, CLevelSnapshotRequest

router = APIRouter(prefix="/c-level-report", tags=["c-level-report"])


async def get_c_level_workspace(services: ApiServices = Depends(get_api_services)) -> AsyncIterator[CLevelWorkspaceUseCase]:
    if services.get_c_level_workspace is None:
        raise HTTPException(status_code=503, detail="C-Level 보고서가 준비되지 않았습니다.")
    async with services.get_c_level_workspace() as use_case:
        yield use_case


def _error(error: Exception) -> HTTPException:
    if isinstance(error, CLevelPreviewExpiredError):
        return HTTPException(status_code=410, detail=str(error))
    if isinstance(error, EntityNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=502, detail="Jira C-Level 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")


@router.get("")
async def get_report(
    response: Response,
    period: Literal["week", "month"] = "week",
    date: CalendarDate | None = None,
    refresh: bool = False,
    actor: str = Depends(require_auth),
    use_case: CLevelWorkspaceUseCase = Depends(get_c_level_workspace),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await use_case.get_report(period, date, refresh, actor)
    except (ValueError, RuntimeError) as error:
        raise _error(error) from error


@router.put("/comments/{issue_key}", response_model=CLevelComment)
async def save_comment(
    issue_key: str,
    body: CLevelCommentRequest,
    request: Request,
    actor: str = Depends(require_auth),
    use_case: CLevelWorkspaceUseCase = Depends(get_c_level_workspace),
    audit: AuditPort = Depends(get_audit),
):
    try:
        result = await use_case.save_comment(
            body.report_token, issue_key, body.delay_reason, body.action_taken,
            body.prevention_plan, body.included, actor,
        )
    except (ValueError, EntityNotFoundError) as error:
        raise _error(error) from error
    audit.record("C_LEVEL_COMMENT_SAVE", ip=get_client_ip(request), issue_key=issue_key, username=actor)
    return result


@router.get("/snapshots", response_model=list[CLevelSnapshotSummary])
async def list_snapshots(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    use_case: CLevelWorkspaceUseCase = Depends(get_c_level_workspace),
):
    return await use_case.list_snapshots(limit, offset)


@router.post("/snapshots", response_model=CLevelSnapshotSummary, status_code=201)
async def save_snapshot(
    body: CLevelSnapshotRequest,
    request: Request,
    actor: str = Depends(require_auth),
    use_case: CLevelWorkspaceUseCase = Depends(get_c_level_workspace),
    audit: AuditPort = Depends(get_audit),
):
    try:
        result = await use_case.save_snapshot(body.report_token, body.title, actor)
    except ValueError as error:
        raise _error(error) from error
    audit.record("C_LEVEL_SNAPSHOT_SAVE", ip=get_client_ip(request), snapshot_id=result.id, username=actor)
    return result


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: int, response: Response, use_case: CLevelWorkspaceUseCase = Depends(get_c_level_workspace)):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await use_case.get_snapshot(snapshot_id)
    except EntityNotFoundError as error:
        raise _error(error) from error
