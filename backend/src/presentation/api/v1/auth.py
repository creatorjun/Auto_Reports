# backend/src/presentation/api/v1/auth.py
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from src.application.services.auth_service import AuthService
from src.presentation.api.deps import get_auth

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


def _set_refresh_cookie(response: Response, token: str, expire_days: int, secure: bool) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=expire_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    auth: AuthService = Depends(get_auth),
):
    if not auth.enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")

    if not auth.is_valid_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    generation = (
        auth.begin_superadmin_session()
        if auth.is_superadmin(body.username, body.password)
        else None
    )
    _set_refresh_cookie(
        response,
        auth.create_refresh_token(body.username, generation),
        auth.refresh_expire_days,
        auth.cookie_secure,
    )
    return TokenResponse(
        access_token=auth.create_access_token(body.username, generation)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
    auth: AuthService = Depends(get_auth),
):
    if not auth.enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        username = auth.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    generation = (
        auth.current_superadmin_generation()
        if username == auth.superadmin_username
        else None
    )
    _set_refresh_cookie(
        response,
        auth.create_refresh_token(username, generation),
        auth.refresh_expire_days,
        auth.cookie_secure,
    )
    return TokenResponse(access_token=auth.create_access_token(username, generation))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/v1/auth")
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
    auth: AuthService = Depends(get_auth),
):
    if not auth.enabled:
        return MeResponse(username="guest", login_required=False)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        username = auth.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return MeResponse(username=username, login_required=True)
