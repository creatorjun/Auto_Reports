# backend/src/presentation/api/v1/reports.py
import dataclasses
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.get_report import GetReportUseCase
from src.presentation.api.deps import get_get_use_case
from src.presentation.schemas.report_schema import AiAnalysisSchema, ReportDetailSchema, ReportSummarySchema, WidgetResultSchema

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=list[ReportSummarySchema])
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    reports = await use_case.get_all(limit=limit, offset=offset)
    return [
        ReportSummarySchema(
            id=r.id,
            week_start=r.week_start,
            week_end=r.week_end,
            report_date=r.report_date,
            created_at=r.created_at,
            sentiment=r.ai_analysis.sentiment if r.ai_analysis else None,
        )
        for r in reports
    ]


@router.get("/latest", response_model=Optional[ReportDetailSchema])
async def get_latest_report(use_case: GetReportUseCase = Depends(get_get_use_case)):
    report = await use_case.get_latest()
    if not report:
        return None
    return _to_detail(report)


@router.get("/{report_id}", response_model=ReportDetailSchema)
async def get_report(
    report_id: int,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    report = await use_case.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_detail(report)


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    deleted = await use_case.delete(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")


def _to_detail(report) -> ReportDetailSchema:
    widgets = {
        k: WidgetResultSchema(
            name=v.name,
            total=v.total,
            jql=v.jql,
            data=dataclasses.asdict(v.data) if v.data is not None else None,
        )
        for k, v in report.widgets.items()
    }
    ai = None
    if report.ai_analysis:
        ai = AiAnalysisSchema(
            summary=report.ai_analysis.summary,
            risks=report.ai_analysis.risks,
            recommendations=report.ai_analysis.recommendations,
            sentiment=report.ai_analysis.sentiment,
        )
    return ReportDetailSchema(
        id=report.id,
        week_start=report.week_start,
        week_end=report.week_end,
        report_date=report.report_date,
        created_at=report.created_at,
        widgets=widgets,
        ai_analysis=ai,
    )
