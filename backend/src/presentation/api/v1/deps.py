# backend/src/presentation/api/v1/deps.py
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.database import get_db_session
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.storage_use_case import StorageUseCase

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    container = request.app.state.container
    if not container.login_enabled:
        return "guest"
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return container.jwt_service().decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_storage_use_case(request: Request) -> StorageUseCase:
    return request.app.state.container.storage_use_case()


async def get_get_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> GetReportUseCase:
    container = request.app.state.container
    return container.get_report_use_case(session)


async def get_site_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SiteUseCase:
    container = request.app.state.container
    return container.site_use_case(session)
