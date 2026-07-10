# backend/src/presentation/api/v1/deps.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import get_db_session
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.security.jwt_service import get_jwt_service
from src.infrastructure.storage.local_storage import get_local_storage_adapter
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.storage_use_case import StorageUseCase
from src.shared.cache import LruCache

_bearer = HTTPBearer(auto_error=False)

_report_cache: LruCache = LruCache(maxsize=64, ttl_seconds=300.0)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    settings = get_settings()
    if not settings.login:
        return "guest"
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return get_jwt_service().decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_storage_use_case() -> StorageUseCase:
    return StorageUseCase(get_local_storage_adapter())


async def get_get_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> GetReportUseCase:
    repository = ReportRepositoryImpl(session)
    return GetReportUseCase(repository=repository, cache=_report_cache)
