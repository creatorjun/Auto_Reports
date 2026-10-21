# backend/src/application/use_cases/jira_notifications.py
import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from src.application.ports.jira_notification_port import (
    JiraNotificationSourcePort,
    JiraNotificationsReconnectRequired,
    JiraNotificationsUnavailable,
)
from src.application.ports.jira_oauth_port import JiraLoginUnavailable
from src.application.ports.jira_user_grant_port import JiraUserGrant, JiraUserGrantStorePort
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.jira_notification import JiraNotificationPage

T = TypeVar("T")


class JiraNotificationsUseCase:
    def __init__(self, source: JiraNotificationSourcePort, grants: JiraUserGrantStorePort) -> None:
        self._source = source
        self._grants = grants
        self._slots = asyncio.Semaphore(8)

    async def execute(
        self, identity: AuthIdentity, category: Literal["direct", "watching"] | None = None,
        cursor: str | None = None, unread_only: bool = False,
    ) -> JiraNotificationPage:
        return await self._with_grant(identity, lambda grant: self._source.fetch(grant, category=category, cursor=cursor, unread_only=unread_only))

    async def mark_read(
        self, identity: AuthIdentity, notification_id: str, group_id: str,
        category: Literal["direct", "watching"],
    ) -> None:
        await self._with_grant(identity, lambda grant: self._source.mark_read(grant, notification_id, group_id, category))

    async def mark_all_read(
        self, identity: AuthIdentity, category: Literal["direct", "watching"] | None = None,
    ) -> None:
        await self._with_grant(identity, lambda grant: self._source.mark_all_read(grant, category=category))

    async def _with_grant(self, identity: AuthIdentity, operation: Callable[[JiraUserGrant], Awaitable[T]]) -> T:
        if identity.auth_provider != "jira":
            raise PermissionError("Jira login is required")
        grant_id = identity.jira_grant_id
        if not grant_id:
            raise JiraNotificationsReconnectRequired()
        try:
            async with asyncio.timeout(35):
                async with self._slots:
                    grant = await self._grants.get(grant_id, identity)
                    if grant is None:
                        raise JiraNotificationsReconnectRequired()
                    result = await operation(grant)
                    if await self._grants.get(grant_id, identity) is None:
                        raise JiraNotificationsReconnectRequired()
        except JiraNotificationsReconnectRequired:
            await self._grants.revoke(grant_id, identity)
            raise
        except (TimeoutError, JiraLoginUnavailable):
            raise JiraNotificationsUnavailable() from None
        return result
