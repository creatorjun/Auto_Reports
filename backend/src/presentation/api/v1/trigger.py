# backend/src/presentation/api/v1/trigger.py
from fastapi import APIRouter, BackgroundTasks, Depends

from src.application.use_cases.generate_report import GenerateReportUseCase
from src.presentation.api.deps import get_generate_use_case
from src.presentation.schemas.report_schema import TriggerResponseSchema

router = APIRouter(prefix="/trigger", tags=["trigger"])

_last_report_id: dict = {}


@router.post("/", response_model=TriggerResponseSchema)
async def trigger_report(
    background_tasks: BackgroundTasks,
    use_case: GenerateReportUseCase = Depends(get_generate_use_case)
):
    report = await use_case.execute()
    return TriggerResponseSchema(
        report_id=report.id,
        message=f"보고서 생성 완료 (ID: {report.id}, 기간: {report.week_start} ~ {report.week_end})"
    )
