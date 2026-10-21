# backend/src/presentation/schemas/jira_notification_schema.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JiraNotificationSchema(BaseModel):
    id: str
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
