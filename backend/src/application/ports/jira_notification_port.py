# backend/src/application/ports/jira_notification_port.py
from abc import ABC, abstractmethod
from typing import Literal

from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.domain.entities.jira_notification import JiraNotificationPage


class JiraNotificationsReconnectRequired(Exception):
    pass


class JiraNotificationsUnavailable(Exception):
    pass


class JiraNotificationSourcePort(ABC):
    @abstractmethod
    async def fetch(
        self,
        grant: JiraUserGrant,
        category: Literal["direct", "watching"] | None = None,
        cursor: str | None = None,
        unread_only: bool = False,
    ) -> JiraNotificationPage:
        raise NotImplementedError

    @abstractmethod
    async def mark_read(
        self,
        grant: JiraUserGrant,
        notification_id: str,
        group_id: str,
        category: Literal["direct", "watching"],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def mark_all_read(
        self,
        grant: JiraUserGrant,
        category: Literal["direct", "watching"] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
