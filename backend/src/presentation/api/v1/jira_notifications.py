# backend/src/presentation/api/v1/jira_notifications.py
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.ports.jira_notification_port import (
    JiraNotificationsReconnectRequired,
    JiraNotificationsUnavailable,
)
from src.application.services.auth_service import AuthService
from src.application.use_cases.jira_notifications import JiraNotificationsUseCase
from src.domain.entities.auth_identity import AuthIdentity
from src.presentation.api.deps import get_api_services, get_auth
from src.presentation.schemas.jira_notification_schema import (
    JiraNotificationReadRequest,
    JiraNotificationReadSchema,
    JiraNotificationSchema,
    JiraNotificationsReadAllRequest,
    JiraNotificationsReadAllSchema,
    JiraNotificationsSchema,
)

router = APIRouter(prefix="/jira/notifications", tags=["jira-notifications"])
_bearer = HTTPBearer(auto_error=False)
_NO_STORE = {"Cache-Control": "no-store"}


async def require_jira_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    auth: AuthService = Depends(get_auth),
) -> AuthIdentity:
    if not auth.enabled:
        raise HTTPException(403, "Jira 로그인 후 알림을 조회할 수 있습니다.", headers=_NO_STORE)
    if credentials is None:
        raise HTTPException(401, "Not authenticated", headers=_NO_STORE)
    try:
        identity = await auth.resolve_access_identity(credentials.credentials)
    except ValueError as error:
        raise HTTPException(401, "Invalid or expired token", headers=_NO_STORE) from error
    if identity.auth_provider != "jira":
        raise HTTPException(403, "Jira 로그인 후 알림을 조회할 수 있습니다.", headers=_NO_STORE)
    request.state.authenticated_username = identity.username
    return identity


def get_jira_notifications(request: Request) -> JiraNotificationsUseCase:
    use_case = get_api_services(request).jira_notifications
    if use_case is None:
        raise HTTPException(503, "Jira 알림 조회가 준비되지 않았습니다.", headers=_NO_STORE)
    return use_case


@router.get("", response_model=JiraNotificationsSchema)
async def list_notifications(
    response: Response,
    category: Literal["all", "direct", "watching"] = Query(default="all"),
    cursor: str | None = Query(default=None, min_length=1, max_length=4096, pattern=r"^[^\x00-\x1f\x7f]+$"),
    unread_only: bool = Query(default=False),
    identity: AuthIdentity = Depends(require_jira_identity),
    use_case: JiraNotificationsUseCase = Depends(get_jira_notifications),
) -> JiraNotificationsSchema:
    response.headers.update(_NO_STORE)
    try:
        page = await use_case.execute(identity, category=None if category == "all" else category, cursor=cursor, unread_only=unread_only)
    except JiraNotificationsReconnectRequired:
        return JiraNotificationsSchema(connection_status="reconnect_required")
    except JiraNotificationsUnavailable as error:
        raise HTTPException(
            503, "Jira 알림을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", headers=_NO_STORE,
        ) from error
    return JiraNotificationsSchema(
        connection_status="connected",
        items=tuple(JiraNotificationSchema(
            id=item.id, group_id=item.group_id, title=item.title, message=item.message, url=item.url,
            actor=item.actor_name, created_at=item.created_at, category=item.category,
            is_read=item.is_read, group_size=item.group_size,
        ) for item in page.items),
        next_cursor=page.next_cursor,
    )


@router.post("/read", response_model=JiraNotificationReadSchema)
async def mark_notification_read(
    body: JiraNotificationReadRequest,
    response: Response,
    identity: AuthIdentity = Depends(require_jira_identity),
    use_case: JiraNotificationsUseCase = Depends(get_jira_notifications),
) -> JiraNotificationReadSchema:
    response.headers.update(_NO_STORE)
    try:
        await use_case.mark_read(identity, body.notification_id, body.group_id, body.category)
    except JiraNotificationsReconnectRequired:
        return JiraNotificationReadSchema(
            connection_status="reconnect_required", notification_id=body.notification_id,
            group_id=body.group_id, is_read=False,
        )
    except JiraNotificationsUnavailable as error:
        raise HTTPException(
            503, "Jira 알림을 읽음 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.", headers=_NO_STORE,
        ) from error
    return JiraNotificationReadSchema(
        connection_status="connected", notification_id=body.notification_id,
        group_id=body.group_id, is_read=True,
    )


@router.post("/read-all", response_model=JiraNotificationsReadAllSchema)
async def mark_all_notifications_read(
    body: JiraNotificationsReadAllRequest,
    response: Response,
    identity: AuthIdentity = Depends(require_jira_identity),
    use_case: JiraNotificationsUseCase = Depends(get_jira_notifications),
) -> JiraNotificationsReadAllSchema:
    response.headers.update(_NO_STORE)
    try:
        await use_case.mark_all_read(identity, category=None if body.category == "all" else body.category)
    except JiraNotificationsReconnectRequired:
        return JiraNotificationsReadAllSchema(connection_status="reconnect_required", category=body.category, is_read=False)
    except JiraNotificationsUnavailable as error:
        raise HTTPException(
            503, "Jira 알림을 모두 읽음 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.", headers=_NO_STORE,
        ) from error
    return JiraNotificationsReadAllSchema(connection_status="connected", category=body.category, is_read=True)
