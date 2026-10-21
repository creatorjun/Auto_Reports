# backend/src/application/services/jira_login_service.py
import asyncio
import hashlib
import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from src.application.ports.jira_login_port import JiraLoginPort, JiraLoginRecord, JiraLoginRepositoryPort
from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.ports.personal_data_port import PersonalDataProfilePort
from src.domain.entities.auth_identity import AuthIdentity


class JiraLoginService(JiraLoginPort):
    def __init__(
        self, repository: JiraLoginRepositoryPort, oauth: JiraOAuthPort,
        profiles: PersonalDataProfilePort, session_days: int = 7, device_days: int = 90,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if type(session_days) is not int or session_days < 1 or type(device_days) is not int or not 1 <= device_days <= 90:
            raise ValueError("Invalid Jira login lifetime")
        self._repository = repository
        self._oauth = oauth
        self._profiles = profiles
        self._session_days = session_days
        self._device_days = device_days
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._closed = False

    @staticmethod
    def _device_hash(cookie: str | None) -> str | None:
        if not isinstance(cookie, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", cookie) is None:
            return None
        return hashlib.sha256(cookie.encode()).hexdigest()

    def _ensure_open(self) -> None:
        if self._closed:
            raise JiraLoginUnavailable("Jira login service is closed")

    def _validate_grant(self, grant: JiraUserGrant, identity: AuthIdentity) -> None:
        if (
            identity.auth_provider != "jira" or identity.username != f"jira:{grant.cloud_id}:{grant.account_id}"
            or not re.fullmatch(r"[A-Za-z0-9-]{1,100}", grant.cloud_id)
            or not re.fullmatch(r"[A-Za-z0-9:_-]{1,128}", grant.account_id)
            or grant.expires_at.tzinfo is None or grant.expires_at <= self._clock()
            or any(not isinstance(value, str) or not value or len(value) > 32768 or any(ord(char) < 32 or ord(char) == 127 for char in value)
                   for value in (grant.access_token, grant.refresh_token))
        ):
            raise JiraLoginDenied("Invalid persistent Jira authorization")

    async def finish_login(self, grant, registered_identity, remember_token=None) -> tuple[AuthIdentity, str]:
        self._ensure_open()
        self._validate_grant(grant, registered_identity)
        now = self._clock()
        cookie = secrets.token_urlsafe(32)
        identity = await self._repository.finish_login(
            grant, registered_identity, device_hash=self._device_hash(cookie),
            previous_device_hash=self._device_hash(remember_token), session_id=secrets.token_urlsafe(32),
            now=now, session_expires_at=now + timedelta(days=self._session_days),
            device_expires_at=now + timedelta(days=self._device_days),
        )
        return identity, cookie

    async def _grant_record(self, *, device_hash: str | None = None, identity: AuthIdentity | None = None) -> JiraLoginRecord | None:
        self._ensure_open()
        try:
            async with asyncio.timeout(30):
                async with self._repository.lease_authorization(now=self._clock(), device_hash=device_hash, identity=identity) as lease:
                    if lease is None:
                        return None
                    if lease.record.grant.expires_at <= self._clock() + timedelta(seconds=60):
                        try:
                            grant = await self._oauth.refresh_user_grant(lease.record.grant)
                            self._validate_grant(grant, lease.record.identity)
                        except JiraLoginDenied:
                            await lease.revoke_authorization()
                            return None
                        save = asyncio.create_task(lease.save_grant(grant, self._clock()))
                        try:
                            await asyncio.shield(save)
                        except asyncio.CancelledError:
                            try:
                                await save
                            except Exception:
                                pass
                            raise
                    return lease.record
        except TimeoutError:
            raise JiraLoginUnavailable("Jira authorization is temporarily unavailable") from None

    async def resume(self, cookie: str) -> AuthIdentity:
        device_hash = self._device_hash(cookie)
        if device_hash is None:
            raise JiraLoginDenied("Remembered Jira login is unavailable")
        record = await self._grant_record(device_hash=device_hash)
        if record is None:
            raise JiraLoginDenied("Remembered Jira login is unavailable")
        try:
            async with asyncio.timeout(30):
                identity = await self._oauth.validate_user_grant(record.grant)
            self._validate_grant(record.grant, identity)
        except JiraLoginDenied:
            await self._repository.revoke_authorization(record.user_id, record.grant)
            raise
        except TimeoutError:
            raise JiraLoginUnavailable("Jira account validation is temporarily unavailable") from None
        try:
            identity = await self._profiles.register_identity(identity)
        except ValueError:
            raise JiraLoginDenied("Jira profile is unavailable") from None
        self._ensure_open()
        now = self._clock()
        return await self._repository.issue_session(
            record, identity, session_id=secrets.token_urlsafe(32), now=now,
            session_expires_at=now + timedelta(days=self._session_days),
            device_expires_at=now + timedelta(days=self._device_days),
        )

    async def resolve(self, identity: AuthIdentity) -> AuthIdentity:
        self._ensure_open()
        resolved = await self._repository.resolve(identity, self._clock())
        if resolved is None:
            raise JiraLoginDenied("Jira login session is no longer available")
        return resolved

    async def get(self, grant_id: str, identity: AuthIdentity) -> JiraUserGrant | None:
        if self._closed or identity.auth_provider != "jira" or identity.jira_grant_id != grant_id:
            return None
        record = await self._grant_record(identity=identity)
        if record is None or await self._repository.resolve(identity, self._clock()) is None:
            return None
        return record.grant

    async def put(self, grant: JiraUserGrant, identity: AuthIdentity) -> str:
        raise ValueError("Persistent Jira login requires a verified profile and browser authorization")

    async def revoke(self, grant_id: str, identity: AuthIdentity) -> None:
        if identity.jira_grant_id == grant_id and identity.auth_provider == "jira":
            await self._repository.revoke_session(identity)

    async def forget(self, cookie: str) -> None:
        device_hash = self._device_hash(cookie)
        if device_hash is not None:
            await self._repository.forget_device(device_hash)

    async def has_device(self, cookie: str) -> bool:
        device_hash = self._device_hash(cookie)
        return bool(not self._closed and device_hash is not None and await self._repository.has_device(device_hash, self._clock()))

    async def reconcile_privacy(self) -> None:
        await self._repository.reconcile_privacy()

    async def clear(self) -> None:
        await self._repository.clear()

    async def aclose(self) -> None:
        self._closed = True
