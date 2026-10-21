# backend/src/application/use_cases/jira_notifications.py
import asyncio
from typing import Literal

from src.application.ports.jira_notification_port import (
    JiraNotificationSourcePort,
    JiraNotificationsReconnectRequired,
    JiraNotificationsUnavailable,
)
from src.application.ports.jira_user_grant_port import JiraUserGrantStorePort
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.jira_notification import JiraNotificationPage


class JiraNotificationsUseCase:
    def __init__(self, source: JiraNotificationSourcePort, grants: JiraUserGrantStorePort) -> None:
        self._source = source
        self._grants = grants
        self._slots = asyncio.Semaphore(8)

    async def execute(
        self, identity: AuthIdentity, category: Literal["direct", "watching"] | None = None,
        cursor: str | None = None,
    ) -> JiraNotificationPage:
        if identity.auth_provider != "jira":
            raise PermissionError("Jira login is required")
        grant_id = identity.jira_grant_id
        if not grant_id:
            raise JiraNotificationsReconnectRequired()
        grant = await self._grants.get(grant_id, identity)
        if grant is None:
            raise JiraNotificationsReconnectRequired()
        try:
            async with asyncio.timeout(35):
                async with self._slots:
                    if await self._grants.get(grant_id, identity) is None:
                        raise JiraNotificationsReconnectRequired()
                    page = await self._source.fetch(grant, category=category, cursor=cursor)
        except JiraNotificationsReconnectRequired:
            await self._grants.revoke(grant_id, identity)
            raise
        except TimeoutError as error:
            raise JiraNotificationsUnavailable() from error
        if await self._grants.get(grant_id, identity) is None:
            raise JiraNotificationsReconnectRequired()
        return page
