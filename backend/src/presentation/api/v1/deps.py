# backend/src/presentation/api/v1/deps.py
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.services.auth_service import AuthService
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.get_report_chart_issues import GetReportChartIssuesUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.sla_dashboard import SlaDashboardUseCase
from src.presentation.api.deps import ApiServices, get_api_services, get_auth

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    auth: AuthService = Depends(get_auth),
) -> str:
    if not auth.enabled:
        request.state.authenticated_username = "guest"
        return "guest"
    token = credentials.credentials if credentials else request.query_params.get("token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        username = auth.decode_access_token(token)
        request.state.authenticated_username = username
        return username
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_superadmin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    auth: AuthService = Depends(get_auth),
) -> str:
    if not auth.enabled:
        raise HTTPException(status_code=403, detail="감사로그는 관리자 로그인 후 조회할 수 있습니다.")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        username = auth.decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not auth.is_superadmin_user(username):
        raise HTTPException(status_code=403, detail="관리자 계정만 감사로그를 조회할 수 있습니다.")
    request.state.authenticated_username = username
    return username


async def get_get_use_case(
    services: ApiServices = Depends(get_api_services),
) -> AsyncIterator[GetReportUseCase]:
    async with services.get_report() as use_case:
        yield use_case


async def get_site_use_case(
    services: ApiServices = Depends(get_api_services),
) -> AsyncIterator[SiteUseCase]:
    async with services.get_site() as use_case:
        yield use_case


async def get_report_chart_issues_use_case(
    services: ApiServices = Depends(get_api_services),
) -> AsyncIterator[GetReportChartIssuesUseCase]:
    async with services.get_report_chart_issues() as use_case:
        yield use_case


async def get_sla_dashboard_use_case(
    services: ApiServices = Depends(get_api_services),
) -> AsyncIterator[SlaDashboardUseCase]:
    async with services.get_sla_dashboard() as use_case:
        yield use_case
