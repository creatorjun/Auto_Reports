# backend/src/presentation/schemas/jira_notification_schema.py
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationIdentifier = Annotated[str, Field(strict=True, min_length=1, max_length=2048, pattern=r"^[^\s\x00-\x1f\x7f-\x9f]+$")]


class JiraNotificationSchema(BaseModel):
    id: str
    group_id: str
    title: str
    message: str
    url: str | None
    actor: str | None
    created_at: datetime
    category: Literal["direct", "watching"]
    is_read: bool
    group_size: int = Field(ge=1)


class JiraNotificationsSchema(BaseModel):
    connection_status: Literal["connected", "reconnect_required"]
    items: tuple[JiraNotificationSchema, ...] = ()
    next_cursor: str | None = None


class JiraNotificationReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notification_id: NotificationIdentifier
    group_id: NotificationIdentifier
    category: Literal["direct", "watching"]


class JiraNotificationReadSchema(BaseModel):
    connection_status: Literal["connected", "reconnect_required"]
    notification_id: str
    group_id: str
    is_read: bool
