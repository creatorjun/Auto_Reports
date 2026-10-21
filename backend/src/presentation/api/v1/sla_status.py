# backend/src/presentation/api/v1/sla_status.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.application.use_cases.sla_status import SlaStatusSourceError, SlaStatusUseCase
from src.presentation.api.deps import get_sla_status_use_case
from src.presentation.schemas.sla_status_schema import SlaStatusSnapshotSchema

router = APIRouter(prefix="/sla-status", tags=["sla-status"])


@router.get("", response_model=SlaStatusSnapshotSchema)
async def get_snapshot(
    response: Response,
    refresh: bool = Query(default=False),
    use_case: SlaStatusUseCase = Depends(get_sla_status_use_case),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await use_case.get_snapshot(refresh=refresh)
    except SlaStatusSourceError as error:
        raise HTTPException(
            status_code=503,
            detail="Jira SLA 현황을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Cache-Control": "no-store"},
        ) from error
