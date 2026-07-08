# backend/src/presentation/api/v1/trigger.py
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.infrastructure.job_runner import JobRunner
from src.presentation.api.deps import get_job_runner
from src.presentation.schemas.report_schema import JobStatusSchema, TriggerAcceptedSchema

router = APIRouter(prefix="/trigger", tags=["trigger"])


@router.post("/", response_model=TriggerAcceptedSchema, status_code=202)
async def trigger_report(
    background_tasks: BackgroundTasks,
    job_runner: JobRunner = Depends(get_job_runner),
):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(job_runner.execute_in_background, job_id)
    return TriggerAcceptedSchema(
        job_id=job_id,
        message="보고서 생성을 시작했습니다.",
    )


@router.get("/{job_id}/status", response_model=JobStatusSchema)
async def get_job_status(
    job_id: str,
    job_runner: JobRunner = Depends(get_job_runner),
):
    job = job_runner.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")
    return JobStatusSchema(
        job_id=job_id,
        status=job["status"],
        report_id=job.get("report_id"),
        error=job.get("error"),
    )
