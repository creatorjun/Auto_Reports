# backend/src/presentation/api/v1/notifications.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.ports.audit_port import AuditPort
from src.application.services.auth_service import AuthService
from src.application.use_cases.notify_sla_digest import NotifySlaDigestUseCase
from src.presentation.api.deps import get_audit, get_auth, get_sla_digest_use_case
from src.presentation.schemas.sla_digest_schema import SlaDigestTriggerRequest, SlaDigestTriggerResponse


_bearer = HTTPBearer(auto_error=False)


async def require_notification_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    auth: AuthService = Depends(get_auth),
) -> str:
    if not auth.enabled or credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        username = (await auth.resolve_access_identity(credentials.credentials)).username
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from error
    request.state.authenticated_username = username
    return username


router = APIRouter(
    prefix="/notifications", tags=["notifications"], dependencies=[Depends(require_notification_auth)],
)


@router.post("/sla-digest/trigger", response_model=SlaDigestTriggerResponse)
async def trigger_sla_digest(
    response: Response,
    body: SlaDigestTriggerRequest = SlaDigestTriggerRequest(),
    use_case: NotifySlaDigestUseCase = Depends(get_sla_digest_use_case),
    audit: AuditPort = Depends(get_audit),
) -> SlaDigestTriggerResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        result = await use_case.trigger(dry_run=body.dry_run)
    except Exception as error:
        audit.record("SLA_DIGEST_TRIGGER_FAILED", dry_run=body.dry_run, error_type=type(error).__name__)
        raise HTTPException(
            status_code=502,
            detail="SLA 조회 또는 메일 발송에 실패했습니다. 서버 로그를 확인해 주세요.",
            headers={"Cache-Control": "no-store"},
        ) from error
    audit.record(
        "SLA_DIGEST_TRIGGER", dry_run=body.dry_run, status=result.status,
        ticket_count=result.ticket_count, sla_count=result.sla_count, recipient_count=result.recipient_count,
    )
    return SlaDigestTriggerResponse.model_validate(result)
