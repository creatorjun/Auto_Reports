# backend/src/presentation/api/v1/reports.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.application.mappers.report_mapper import ReportMapper
from src.application.use_cases.get_report import GetReportUseCase
from src.presentation.api.deps import get_get_use_case
from src.presentation.schemas.report_schema import ReportDetailSchema, ReportSummarySchema

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=list[ReportSummarySchema])
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    reports = await use_case.get_all(limit=limit, offset=offset)
    return [ReportMapper.to_summary(r) for r in reports]


@router.get("/latest", response_model=Optional[ReportDetailSchema])
async def get_latest_report(use_case: GetReportUseCase = Depends(get_get_use_case)):
    report = await use_case.get_latest()
    if not report:
        return None
    return ReportMapper.to_detail(report)


@router.get("/{report_id}", response_model=ReportDetailSchema)
async def get_report(
    report_id: int,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    report = await use_case.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportMapper.to_detail(report)


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    deleted = await use_case.delete(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
