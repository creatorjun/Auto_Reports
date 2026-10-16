# backend/src/presentation/api/v1/auth.py
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from time import time
from urllib.parse import urlsplit

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable
from src.application.services.auth_service import AuthService
from src.application.ports.audit_port import AuditPort
from src.domain.entities.auth_identity import AuthIdentity
from src.presentation.api.deps import get_audit, get_auth
from src.presentation.http.client_ip import get_client_ip

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
JIRA_STATE_COOKIE = "jira_oauth_state"
JIRA_COOKIE_PATH = "/api/v1/auth/jira"


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str
    auth_provider: str = "local"
    is_superadmin: bool = False


class MeResponse(BaseModel):
    username: str
    login_required: bool
    is_superadmin: bool = False
    display_name: str = ""
    auth_provider: str = "local"


def _token_response(auth: AuthService, identity: AuthIdentity, generation: int | None = None) -> TokenResponse:
    return TokenResponse(
        access_token=auth.create_identity_access_token(identity, generation),
        username=identity.username,
        display_name=identity.display_name,
        auth_provider=identity.auth_provider,
        is_superadmin=identity.auth_provider == "local" and auth.is_superadmin_user(identity.username),
    )


def _require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-site authentication request rejected")
    if origin:
        try:
            parsed = urlsplit(origin)
            matches = parsed.scheme == request.url.scheme and parsed.netloc == request.url.netloc
        except ValueError:
            matches = False
        if not matches:
            raise HTTPException(status_code=403, detail="Cross-site authentication request rejected")


def _jira_redirect(result: str, auth: AuthService) -> RedirectResponse:
    response = RedirectResponse(f"/login?jira={result}", status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.delete_cookie(
        JIRA_STATE_COOKIE, path=JIRA_COOKIE_PATH,
        secure=auth.cookie_secure, httponly=True, samesite="lax",
    )
    return response


@router.get("/providers")
async def providers(auth: AuthService = Depends(get_auth)):
    return {"jira": {"enabled": auth.jira_enabled}}


@router.post("/jira/start")
async def jira_start(request: Request, response: Response, auth: AuthService = Depends(get_auth)):
    _require_same_origin(request)
    try:
        state, authorization_url = auth.begin_jira_login()
    except JiraLoginUnavailable:
        raise HTTPException(status_code=503, detail="Jira login is not available") from None
    response.set_cookie(
        JIRA_STATE_COOKIE, state,
        max_age=auth.jira_state_expire_seconds,
        httponly=True, secure=auth.cookie_secure, samesite="lax", path=JIRA_COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"authorization_url": authorization_url}


@router.get("/jira/callback")
async def jira_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    jira_state: str | None = Cookie(default=None, alias=JIRA_STATE_COOKIE),
    auth: AuthService = Depends(get_auth),
    audit: AuditPort = Depends(get_audit),
):
    try:
        auth.consume_jira_state(state, jira_state)
        if error or not code:
            raise JiraLoginDenied("Jira authorization was denied")
        identity = await auth.authenticate_jira(code)
    except JiraLoginDenied:
        audit.record("LOGIN_FAILED", ip=get_client_ip(request), provider="jira")
        return _jira_redirect("denied", auth)
    except JiraLoginUnavailable:
        return _jira_redirect("unavailable", auth)
    response = _jira_redirect("success", auth)
    _set_refresh_cookie(
        response, auth.create_identity_refresh_token(identity),
        auth.refresh_expire_days, auth.cookie_secure, identity.session_expires_at,
    )
    audit.record("LOGIN_SUCCESS", ip=get_client_ip(request), username=identity.username, provider="jira")
    return response


def _set_refresh_cookie(
    response: Response, token: str, expire_days: int, secure: bool, session_expires_at: int | None = None,
) -> None:
    max_age = expire_days * 86400
    if session_expires_at is not None:
        max_age = max(0, min(max_age, session_expires_at - int(time())))
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    auth: AuthService = Depends(get_auth),
    audit: AuditPort = Depends(get_audit),
):
    if not auth.enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")

    _require_same_origin(request)

    if not auth.is_valid_credentials(body.username, body.password):
        audit.record("LOGIN_FAILED", ip=get_client_ip(request), username=body.username)
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
    audit.record("LOGIN_SUCCESS", ip=get_client_ip(request), username=body.username)
    response.headers["Cache-Control"] = "no-store"
    return _token_response(auth, AuthIdentity(body.username, body.username), generation)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    request: Request,
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
    auth: AuthService = Depends(get_auth),
):
    if not auth.enabled:
        raise HTTPException(status_code=404, detail="Auth not enabled")
    _require_same_origin(request)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        identity = auth.decode_refresh_identity(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    generation = (
        auth.current_superadmin_generation()
        if identity.auth_provider == "local" and auth.is_superadmin_user(identity.username)
        else None
    )
    _set_refresh_cookie(
        response,
        auth.create_identity_refresh_token(identity, generation),
        auth.refresh_expire_days,
        auth.cookie_secure,
        identity.session_expires_at,
    )
    response.headers["Cache-Control"] = "no-store"
    return _token_response(auth, identity, generation)


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    refresh_token: str = Cookie(default=None, alias=REFRESH_COOKIE),
    auth: AuthService = Depends(get_auth),
    audit: AuditPort = Depends(get_audit),
):
    _require_same_origin(request)
    username = None
    if auth.enabled and refresh_token:
        try:
            username = auth.decode_refresh_token(refresh_token)
        except ValueError:
            pass
    if username is not None:
        audit.record("LOGOUT", ip=get_client_ip(request), username=username)
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
        identity = auth.decode_refresh_identity(refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return MeResponse(
        username=identity.username,
        display_name=identity.display_name,
        auth_provider=identity.auth_provider,
        login_required=True,
        is_superadmin=identity.auth_provider == "local" and auth.is_superadmin_user(identity.username),
    )
