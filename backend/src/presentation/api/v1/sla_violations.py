# backend/src/presentation/api/v1/sla_violations.py
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from src.application.errors import EntityNotFoundError
from src.application.ports.audit_port import AuditPort
from src.application.use_cases.sla_violation_report import (
    SlaViolationGenerationInProgressError,
    SlaViolationReportUseCase,
    SlaViolationSourceError,
)
from src.presentation.api.deps import get_audit
from src.presentation.api.v1.deps import get_sla_violation_use_case
from src.presentation.schemas.sla_violation_schema import (
    SlaViolationCreateSchema,
    SlaViolationReportSchema,
    SlaViolationReportSummarySchema,
)

router = APIRouter(prefix="/sla-violations", tags=["sla-violations"])


@router.post("", response_model=SlaViolationReportSchema, status_code=201)
async def create_report(
    body: SlaViolationCreateSchema,
    request: Request,
    response: Response,
    use_case: SlaViolationReportUseCase = Depends(get_sla_violation_use_case),
    audit: AuditPort = Depends(get_audit),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        report = await use_case.generate(
            period=body.period,
            selected_date=body.date,
            generated_by=getattr(request.state, "authenticated_username", "system"),
        )
    except SlaViolationGenerationInProgressError as error:
        raise HTTPException(status_code=409, detail="SLA 위반 보고서를 생성 중입니다. 완료 후 다시 시도해 주세요.") from error
    except SlaViolationSourceError as error:
        raise HTTPException(status_code=502, detail="Jira SLA 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    audit.record(
        "SLA_VIOLATION_REPORT_CREATE",
        report_id=report.id,
        period=report.period,
        selected_date=report.selected_date.isoformat(),
        ticket_count=report.ticket_count,
        initial_response_count=report.initial_response_count,
        resolution_count=report.resolution_count,
    )
    return report


@router.get("/latest", response_model=SlaViolationReportSchema | None)
async def latest_report(
    response: Response,
    use_case: SlaViolationReportUseCase = Depends(get_sla_violation_use_case),
):
    response.headers["Cache-Control"] = "no-store"
    return await use_case.get_latest()


@router.get("/history", response_model=list[SlaViolationReportSummarySchema])
async def report_history(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    use_case: SlaViolationReportUseCase = Depends(get_sla_violation_use_case),
):
    response.headers["Cache-Control"] = "no-store"
    return await use_case.list_summaries(limit=limit, offset=offset)


@router.get("/{report_id}", response_model=SlaViolationReportSchema)
async def saved_report(
    response: Response,
    report_id: int = Path(ge=1),
    use_case: SlaViolationReportUseCase = Depends(get_sla_violation_use_case),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await use_case.get_by_id(report_id)
    except EntityNotFoundError as error:
        raise HTTPException(status_code=404, detail="SLA 위반 보고서를 찾을 수 없습니다.") from error
