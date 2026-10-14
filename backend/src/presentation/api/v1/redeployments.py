# backend/src/presentation/api/v1/redeployments.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.application.use_cases.redeployment_report import RedeploymentGenerationInProgress, RedeploymentReportUseCase
from src.domain.entities.redeployment_report import RedeploymentReport
from src.presentation.api.deps import get_audit
from src.application.ports.audit_port import AuditPort
from src.presentation.api.v1.deps import get_redeployment_use_case

router = APIRouter(prefix="/redeployments", tags=["redeployments"])


@router.get("/latest", response_model=RedeploymentReport | None)
async def latest(response: Response, use_case: RedeploymentReportUseCase = Depends(get_redeployment_use_case)):
    response.headers["Cache-Control"] = "no-store"
    return await use_case.get_latest()


@router.post("", response_model=RedeploymentReport)
async def generate(request: Request, response: Response,
                   use_case: RedeploymentReportUseCase = Depends(get_redeployment_use_case),
                   audit: AuditPort = Depends(get_audit)):
    response.headers["Cache-Control"] = "no-store"
    try:
        report = await use_case.generate(getattr(request.state, "authenticated_username", "system"), force=True)
    except RedeploymentGenerationInProgress as error:
        raise HTTPException(409, "재배포 보고서를 갱신 중입니다. 잠시 후 다시 확인해 주세요.") from error
    except RuntimeError as error:
        raise HTTPException(502, "Jira 재배포 정보를 불러오지 못했습니다. 마지막 보고서를 유지합니다.") from error
    audit.record("REDEPLOYMENT_REPORT_CREATE", report_id=report.id, ticket_count=len(report.tickets))
    return report
