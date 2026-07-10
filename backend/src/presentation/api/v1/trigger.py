# backend/src/presentation/api/v1/trigger.py
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.application.ports.job_runner_port import JobRunnerPort
from src.presentation.api.deps import get_job_runner
from src.presentation.schemas.report_schema import (
    JobStatus,
    JobStatusSchema,
    TriggerAcceptedSchema,
    TriggerRequest,
)

router = APIRouter(prefix="/trigger", tags=["trigger"])

KST = ZoneInfo("Asia/Seoul")


@router.post("/", response_model=TriggerAcceptedSchema, status_code=202)
async def trigger_report(
    body: TriggerRequest = TriggerRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    job_runner: JobRunnerPort = Depends(get_job_runner),
):
    start_dt: datetime | None = None
    end_dt: datetime | None = None

    if body.start_date:
        start_dt = datetime.strptime(body.start_date, "%Y-%m-%d").replace(tzinfo=KST)
    if body.end_date:
        end_dt = datetime.strptime(body.end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=KST
        )

    job_id = str(uuid.uuid4())
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
