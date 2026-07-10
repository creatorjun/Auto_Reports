# backend/src/presentation/api/v1/auth.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response
from jose import JWTError, jwt
from pydantic import BaseModel

from src.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
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


def _create_token(subject: str, token_type: str, expire_delta: timedelta) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {"sub": subject, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


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

    username_ok = body.username == settings.admin_username
    password_ok = body.password == settings.admin_password
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = _create_token(
        body.username,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    refresh_token = _create_token(
        body.username,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.jwt_refresh_expire_days),
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(response: Response, refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE)):
    settings = get_settings()
    if not settings.login:
        raise HTTPException(status_code=404, detail="Auth not enabled")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != REFRESH_TOKEN_TYPE:
            raise ValueError
        username: str = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = _create_token(
        username,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    new_refresh = _create_token(
        username,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.jwt_refresh_expire_days),
    )
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


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

    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != REFRESH_TOKEN_TYPE:
            raise ValueError
        return MeResponse(username=payload["sub"], login_required=True)
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Token expired or invalid")
