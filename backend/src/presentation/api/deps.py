# backend/src/presentation/api/deps.py
from collections.abc import Callable
from dataclasses import dataclass
from typing import AsyncContextManager

from fastapi import HTTPException, Request

from src.application.ports.audit_port import AuditPort
from src.application.ports.job_runner_port import JobRunnerPort
from src.application.services.auth_service import AuthService
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.get_report_chart_issues import GetReportChartIssuesUseCase
from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.use_cases.search import SearchUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.sla_dashboard import SlaDashboardUseCase
from src.application.use_cases.sla_violation_report import SlaViolationReportUseCase
from src.application.use_cases.redeployment_report import RedeploymentReportUseCase
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.application.use_cases.storage_use_case import StorageUseCase
from src.application.use_cases.audit_logs import AuditLogsUseCase
from src.application.use_cases.notify_sla_digest import NotifySlaDigestUseCase
from src.presentation.http.request_audit import RequestAudit


@dataclass(frozen=True)
class ApiServices:
    auth: AuthService
    audit: AuditPort
    jira_base_url: str
    job_runner: JobRunnerPort
    partner: PartnerUseCase
    search: SearchUseCase
    storage: StorageUseCase
    get_report: Callable[[], AsyncContextManager[GetReportUseCase]]
    get_site: Callable[[], AsyncContextManager[SiteUseCase]]
    get_sla_dashboard: Callable[[], AsyncContextManager[SlaDashboardUseCase]]
    get_report_chart_issues: Callable[[], AsyncContextManager[GetReportChartIssuesUseCase]]
    issue_management: IssueManagementUseCase | None = None
    audit_logs: AuditLogsUseCase | None = None
    get_sla_violation: Callable[[], AsyncContextManager[SlaViolationReportUseCase]] | None = None
    get_redeployment: Callable[[], AsyncContextManager[RedeploymentReportUseCase]] | None = None
    notify_sla_digest: NotifySlaDigestUseCase | None = None


def get_api_services(request: Request) -> ApiServices:
    return request.app.state.services


def get_job_runner(request: Request) -> JobRunnerPort:
    return get_api_services(request).job_runner


def get_audit(request: Request) -> AuditPort:
    return RequestAudit(get_api_services(request).audit, request)


def get_auth(request: Request) -> AuthService:
    return get_api_services(request).auth


def get_audit_logs(request: Request) -> AuditLogsUseCase:
    use_case = get_api_services(request).audit_logs
    if use_case is None:
        raise HTTPException(status_code=503, detail="감사로그 조회가 준비되지 않았습니다.")
    return use_case


def get_partner_use_case(request: Request) -> PartnerUseCase:
    return get_api_services(request).partner


def get_search_use_case(request: Request) -> SearchUseCase:
    return get_api_services(request).search


def get_storage_use_case(request: Request) -> StorageUseCase:
    return get_api_services(request).storage


def get_sla_digest_use_case(request: Request) -> NotifySlaDigestUseCase:
    use_case = get_api_services(request).notify_sla_digest
    if use_case is None:
        raise HTTPException(
            status_code=503, detail="SLA 일일 알림이 비활성화되어 있습니다.", headers={"Cache-Control": "no-store"},
        )
    return use_case
