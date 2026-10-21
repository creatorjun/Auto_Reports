# backend/src/domain/entities/jira_notification.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class JiraNotification:
    id: str
    group_id: str
    group_size: int
    category: Literal["direct", "watching"]
    is_read: bool
    created_at: datetime
    title: str
    message: str
    actor_name: str | None
    url: str | None


@dataclass(frozen=True)
class JiraNotificationPage:
    items: tuple[JiraNotification, ...]
    next_cursor: str | None
