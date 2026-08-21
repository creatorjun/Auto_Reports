# backend/src/presentation/api/deps.py
from collections.abc import Callable
from dataclasses import dataclass
from typing import AsyncContextManager

from fastapi import Request

from src.application.ports.audit_port import AuditPort
from src.application.ports.jira_port import JiraPort
from src.application.ports.job_runner_port import JobRunnerPort
from src.application.services.auth_service import AuthService
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.storage_use_case import StorageUseCase


@dataclass(frozen=True)
class ApiServices:
    auth: AuthService
    audit: AuditPort
    jira: JiraPort
    jira_base_url: str
    project_key: str
    job_runner: JobRunnerPort
    partner: PartnerUseCase
    storage: StorageUseCase
    get_report: Callable[[], AsyncContextManager[GetReportUseCase]]
    get_site: Callable[[], AsyncContextManager[SiteUseCase]]


def get_api_services(request: Request) -> ApiServices:
    return request.app.state.services


def get_job_runner(request: Request) -> JobRunnerPort:
    return get_api_services(request).job_runner


def get_jira(request: Request) -> JiraPort:
    return get_api_services(request).jira


def get_audit(request: Request) -> AuditPort:
    return get_api_services(request).audit


def get_auth(request: Request) -> AuthService:
    return get_api_services(request).auth


def get_partner_use_case(request: Request) -> PartnerUseCase:
    return get_api_services(request).partner


def get_storage_use_case(request: Request) -> StorageUseCase:
    return get_api_services(request).storage
