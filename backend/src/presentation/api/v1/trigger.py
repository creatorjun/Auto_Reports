# backend/src/presentation/api/v1/trigger.py
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from src.application.ports.job_runner_port import JobRunnerPort
from src.presentation.api.deps import get_job_runner
from src.presentation.schemas.report_schema import (
    JobStatus,
    JobStatusSchema,
    TriggerAcceptedSchema,
    TriggerRequest,
)
from src.shared.audit_helper import get_client_ip
from src.shared.audit_logger import get_audit_logger

router = APIRouter(prefix="/trigger", tags=["trigger"])

KST = ZoneInfo("Asia/Seoul")
_audit = get_audit_logger()


@router.post("/", response_model=TriggerAcceptedSchema, status_code=202)
async def trigger_report(
    request: Request,
    body: TriggerRequest = TriggerRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    job_runner: JobRunnerPort = Depends(get_job_runner),
):
    if job_runner.is_running:
        raise HTTPException(
            status_code=409,
            detail=f"이미 실행 중인 보고서 생성 작업이 있습니다. (job_id={job_runner.current_job_id()})",
        )

    start_dt: datetime | None = None
    end_dt: datetime | None = None

    if body.start_date:
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d").replace(tzinfo=KST)
    if body.end_date:
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=KST
        )

    job_id = str(uuid.uuid4())
    ip = get_client_ip(request)
    _audit.audit(
        "REPORT_TRIGGER | ip=%s | job_id=%s | start=%s | end=%s",
        ip, job_id,
        body.start_date or "auto",
        body.end_date or "auto",
    )
    background_tasks.add_task(
        job_runner.execute_in_background, job_id, start_dt, end_dt
    )
    return TriggerAcceptedSchema(
        job_id=job_id,
        message="보고서 생성을 시작했습니다.",
    )


@router.get("/{job_id}/status", response_model=JobStatusSchema)
async def get_job_status(
    job_id: str,
    job_runner: JobRunnerPort = Depends(get_job_runner),
):
    record = await job_runner.get_job_status(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")
    return JobStatusSchema(
        job_id=record.job_id,
        status=record.status,
        report_id=record.report_id,
        error=record.error,
    )
