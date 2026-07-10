# backend/src/presentation/api/v1/auth.py
from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.jwt_service import REFRESH_COOKIE_NAME, get_jwt_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    username: str
    login_required: bool


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.jwt_refresh_expire_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response):
    settings = get_settings()
    if not settings.login:
        raise HTTPException(status_code=404, detail="Auth not enabled")

    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    svc = get_jwt_service()
    _set_refresh_cookie(response, svc.create_refresh_token(body.username))
    return TokenResponse(access_token=svc.create_access_token(body.username))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE)):
    settings = get_settings()
    if not settings.login:
        raise HTTPException(status_code=404, detail="Auth not enabled")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    svc = get_jwt_service()
    try:
        username = svc.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    _set_refresh_cookie(response, svc.create_refresh_token(username))
    return TokenResponse(access_token=svc.create_access_token(username))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/v1/auth")
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE)):
    settings = get_settings()
    if not settings.login:
        return MeResponse(username="guest", login_required=False)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    svc = get_jwt_service()
    try:
        username = svc.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return MeResponse(username=username, login_required=True)
