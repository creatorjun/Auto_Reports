# backend/src/presentation/api/v1/deps.py
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.jwt_service import get_jwt_service
from src.infrastructure.storage.local_storage import get_local_storage_adapter
from src.application.use_cases.storage_use_case import StorageUseCase

_bearer = HTTPBearer(auto_error=False)


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
