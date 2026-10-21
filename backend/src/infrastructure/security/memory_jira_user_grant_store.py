# backend/src/infrastructure/security/memory_jira_user_grant_store.py
import asyncio
import re
import secrets
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timezone
from time import monotonic

from src.application.ports.jira_user_grant_port import JiraUserGrant, JiraUserGrantStorePort
from src.domain.entities.auth_identity import AuthIdentity


class MemoryJiraUserGrantStore(JiraUserGrantStorePort):
    def __init__(
        self,
        max_entries: int = 1024,
        clock: Callable[[], float] = monotonic,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if type(max_entries) is not int or not 1 <= max_entries <= 1024:
            raise ValueError("Jira user grant capacity must be between 1 and 1024")
        self._max_entries = max_entries
        self._clock = clock
        self._now = now
        self._entries: OrderedDict[str, tuple[JiraUserGrant, float]] = OrderedDict()
        self._expiry_timer: asyncio.TimerHandle | None = None
        self._closed = False

    def _prune(self) -> None:
        current = self._clock()
        for grant_id in tuple(self._entries):
            if self._entries[grant_id][1] <= current:
                del self._entries[grant_id]

    def _schedule_expiry(self) -> None:
        if self._expiry_timer is not None:
            self._expiry_timer.cancel()
            self._expiry_timer = None
        if self._entries and not self._closed:
            delay = max(0.001, min(deadline for _, deadline in self._entries.values()) - self._clock())
            self._expiry_timer = asyncio.get_running_loop().call_later(delay, self._expire)

    def _expire(self) -> None:
        self._expiry_timer = None
        self._prune()
        self._schedule_expiry()

    @staticmethod
    def _owned(grant: JiraUserGrant, identity: AuthIdentity) -> bool:
        return identity.auth_provider == "jira" and identity.username == f"jira:{grant.cloud_id}:{grant.account_id}"

    async def put(self, grant: JiraUserGrant, identity: AuthIdentity) -> str:
        if self._closed:
            raise ValueError("Jira user grant store is closed")
        current = self._now() if self._now is not None else datetime.now(timezone.utc)
        if (
            not self._owned(grant, identity)
            or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", grant.cloud_id)
            or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", grant.account_id)
            or not isinstance(grant.access_token, str) or not grant.access_token or len(grant.access_token) > 32768
            or any(ord(character) < 32 or ord(character) == 127 for character in grant.access_token)
            or grant.expires_at.tzinfo is None or current.tzinfo is None
        ):
            raise ValueError("Invalid Jira user grant")
        remaining = (grant.expires_at - current).total_seconds()
        if remaining <= 0:
            raise ValueError("Jira user grant has expired")
        self._prune()
        while len(self._entries) >= self._max_entries:
            self._entries.popitem(last=False)
        grant_id = secrets.token_urlsafe(32)
        while grant_id in self._entries:
            grant_id = secrets.token_urlsafe(32)
        self._entries[grant_id] = (grant, self._clock() + remaining)
        self._schedule_expiry()
        return grant_id

    async def get(self, grant_id: str, identity: AuthIdentity) -> JiraUserGrant | None:
        self._prune()
        if self._closed or identity.jira_grant_id != grant_id:
            return None
        item = self._entries.get(grant_id)
        if item is None or not self._owned(item[0], identity):
            return None
        return item[0]

    async def revoke(self, grant_id: str, identity: AuthIdentity) -> None:
        if await self.get(grant_id, identity) is not None:
            self._entries.pop(grant_id, None)
            self._schedule_expiry()

    async def clear(self) -> None:
        self._entries.clear()
        self._schedule_expiry()

    async def aclose(self) -> None:
        self._closed = True
        await self.clear()
