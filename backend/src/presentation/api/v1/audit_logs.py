# backend/src/presentation/api/v1/audit_logs.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.application.ports.audit_log_reader_port import AuditLogReadError
from src.application.use_cases.audit_logs import AuditLogsUseCase
from src.domain.entities.audit_log import AuditLogPage, AuditLogQuery
from src.presentation.api.deps import get_audit_logs
from src.presentation.api.v1.deps import require_superadmin

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"], dependencies=[Depends(require_superadmin)])


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    response: Response,
    start_date: date | None = None,
    end_date: date | None = None,
    event: str = Query(default="", max_length=200),
    username: str = Query(default="", max_length=200),
    ip: str = Query(default="", max_length=200),
    search: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=9900),
    use_case: AuditLogsUseCase = Depends(get_audit_logs),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        return await use_case.execute(AuditLogQuery(start_date, end_date, event.strip(), username.strip(), ip.strip(), search.strip(), limit, offset))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except AuditLogReadError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
