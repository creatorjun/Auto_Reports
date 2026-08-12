# backend/src/presentation/api/v1/trigger.py
import json
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.application.ports.audit_port import AuditPort
from src.presentation.mappers.job_mapper import JobMapper
from src.application.ports.job_runner_port import JobRunnerPort
from src.presentation.api.deps import get_audit, get_job_runner
from src.presentation.schemas.report_schema import (
    JobStatusSchema,
    TriggerAcceptedSchema,
    TriggerRequest,
)
from src.presentation.http.client_ip import get_client_ip

router = APIRouter(prefix="/trigger", tags=["trigger"])

KST = ZoneInfo("Asia/Seoul")

_SSE_WAIT_TIMEOUT    = 30.0
_SSE_TIMEOUT_SECONDS = 300
_SSE_KEEPALIVE_EVERY = 15.0


@router.post("/", response_model=TriggerAcceptedSchema, status_code=202)
async def trigger_report(
    request: Request,
    body: TriggerRequest = TriggerRequest(),
    job_runner: JobRunnerPort = Depends(get_job_runner),
    audit: AuditPort = Depends(get_audit),
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
    await job_runner.submit(job_id, start_dt, end_dt)

    ip = get_client_ip(request)
    audit.record(
        "REPORT_TRIGGER",
        ip=ip,
        job_id=job_id,
        start=body.start_date or "auto",
        end=body.end_date or "auto",
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
    return JobMapper.to_schema(record)


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    request: Request,
    job_runner: JobRunnerPort = Depends(get_job_runner),
):
    record = await job_runner.get_job_status(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")

    async def event_generator():
        start_time    = time.monotonic()
        last_keepalive = time.monotonic()

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= _SSE_TIMEOUT_SECONDS:
                yield _sse_event("timeout", {"error": "job timed out"})
                break

            if await request.is_disconnected():
                break

            current = await job_runner.get_job_status(job_id)
            if current is None:
                yield _sse_event("error", {"error": "job not found"})
                break

            schema = JobMapper.to_schema(current)
            payload = schema.model_dump()

            if schema.status in ("done", "error"):
                yield _sse_event("done", payload)
                break

            yield _sse_event("status", payload)

            await job_runner.wait_for_update(
                job_id,
                current.status,
                timeout=_SSE_WAIT_TIMEOUT,
            )

            if time.monotonic() - last_keepalive >= _SSE_KEEPALIVE_EVERY:
                yield ": keepalive\n\n"
                last_keepalive = time.monotonic()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
