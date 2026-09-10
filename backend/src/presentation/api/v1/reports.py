# backend/src/presentation/api/v1/reports.py
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.application.ports.audit_port import AuditPort
from src.presentation.mappers.report_mapper import ReportMapper
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.get_report_chart_issues import GetReportChartIssuesUseCase
from src.domain.entities.report_chart import ReportChartKind, ReportChartSelection
from src.presentation.api.deps import get_audit
from src.presentation.api.v1.deps import get_get_use_case, get_report_chart_issues_use_case
from src.presentation.schemas.report_chart_schema import ReportChartIssueResultSchema
from src.presentation.schemas.report_schema import ReportDetailSchema, ReportSummarySchema
from src.presentation.http.client_ip import get_client_ip

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


@router.get("/annual/{year}", response_model=ReportDetailSchema)
async def get_annual_report(
    year: int,
    use_case: GetReportUseCase = Depends(get_get_use_case),
):
    report = await use_case.get_annual(year)
    if not report:
        raise HTTPException(status_code=404, detail="Annual report not found")
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


@router.get("/{report_id}/chart-issues", response_model=ReportChartIssueResultSchema)
async def get_report_chart_issues(
    report_id: int,
    chart: ReportChartKind,
    month: int | None = Query(default=None, ge=1, le=12),
    issue_type: str | None = Query(default=None, min_length=1, max_length=200),
    semester: Literal["h1", "h2"] | None = None,
    partner: str | None = Query(default=None, min_length=1, max_length=200),
    cause: str | None = Query(default=None, min_length=1, max_length=200),
    assignee: str | None = Query(default=None, min_length=1, max_length=200),
    filter_types: bool = False,
    selected_types: list[str] | None = Query(default=None, max_length=50),
    filter_statuses: bool = False,
    selected_statuses: list[str] | None = Query(default=None, max_length=50),
    sla_status: Literal["all", "met", "violated"] = "all",
    use_case: GetReportChartIssuesUseCase = Depends(get_report_chart_issues_use_case),
):
    try:
        selection = ReportChartSelection(
            chart=chart, month=month, issue_type=issue_type, semester=semester,
            partner=partner, cause=cause, assignee=assignee,
            selected_types=tuple(selected_types or []) if filter_types else None,
            selected_statuses=tuple(selected_statuses or []) if filter_statuses else None,
            sla_status=sla_status,
        )
        return await use_case.execute(report_id, selection)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail="Jira 이슈 상세를 불러오지 못했습니다.") from error


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    request: Request,
    use_case: GetReportUseCase = Depends(get_get_use_case),
    audit: AuditPort = Depends(get_audit),
):
    deleted = await use_case.delete(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    ip = get_client_ip(request)
    audit.record("REPORT_DELETE", ip=ip, report_id=report_id)
