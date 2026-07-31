# backend/src/presentation/api/v1/auth.py
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel

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


def _set_refresh_cookie(response: Response, token: str, expire_days: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=expire_days * 86400,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response):
    container = request.app.state.container
    if not container.login_enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")

    if not container.is_valid_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    svc = container.jwt_service()

    if container.is_superadmin(body.username, body.password):
        gen = svc.bump_superadmin_generation()
        _set_refresh_cookie(response, svc.create_refresh_token(body.username, generation=gen), container.jwt_refresh_expire_days)
        return TokenResponse(access_token=svc.create_access_token(body.username, generation=gen))

    _set_refresh_cookie(response, svc.create_refresh_token(body.username), container.jwt_refresh_expire_days)
    return TokenResponse(access_token=svc.create_access_token(body.username))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE)):
    container = request.app.state.container
    if not container.login_enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    svc = container.jwt_service()
    try:
        username = svc.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    gen = svc.current_superadmin_generation() if username == container.superadmin_username else None
    _set_refresh_cookie(response, svc.create_refresh_token(username, generation=gen), container.jwt_refresh_expire_days)
    return TokenResponse(access_token=svc.create_access_token(username, generation=gen))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/v1/auth")
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeResponse)
async def me(request: Request, refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE)):
    container = request.app.state.container
    if not container.login_enabled:
        return MeResponse(username="guest", login_required=False)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    svc = container.jwt_service()
    try:
        username = svc.decode_refresh_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return MeResponse(username=username, login_required=True)
