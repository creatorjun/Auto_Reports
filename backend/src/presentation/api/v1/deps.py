# backend/src/presentation/api/v1/deps.py
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.services.auth_service import AuthService
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.presentation.api.deps import ApiServices, get_api_services, get_auth

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    auth: AuthService = Depends(get_auth),
) -> str:
    if not auth.enabled:
        return "guest"
    token = credentials.credentials if credentials else request.query_params.get("token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return auth.decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


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
