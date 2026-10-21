# backend/src/application/ports/jira_login_port.py
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime

from src.application.ports.jira_user_grant_port import JiraUserGrant, JiraUserGrantAccessPort
from src.domain.entities.auth_identity import AuthIdentity


@dataclass(frozen=True)
class JiraLoginRecord:
    user_id: int
    device_hash: str = field(repr=False)
    generation: int
    identity: AuthIdentity
    grant: JiraUserGrant = field(repr=False)


class JiraLoginLeasePort(ABC):
    record: JiraLoginRecord

    @abstractmethod
    async def save_grant(self, grant: JiraUserGrant, now: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_authorization(self) -> None:
        raise NotImplementedError


class JiraLoginRepositoryPort(ABC):
    @abstractmethod
    def lease_authorization(
        self, *, now: datetime, device_hash: str | None = None,
        identity: AuthIdentity | None = None,
    ) -> AbstractAsyncContextManager[JiraLoginLeasePort | None]:
        raise NotImplementedError

    @abstractmethod
    async def finish_login(
        self, grant: JiraUserGrant, identity: AuthIdentity, *, device_hash: str,
        previous_device_hash: str | None, session_id: str, now: datetime,
        session_expires_at: datetime, device_expires_at: datetime,
    ) -> AuthIdentity:
        raise NotImplementedError

    @abstractmethod
    async def issue_session(
        self, record: JiraLoginRecord, identity: AuthIdentity, *, session_id: str,
        now: datetime, session_expires_at: datetime, device_expires_at: datetime,
    ) -> AuthIdentity:
        raise NotImplementedError

    @abstractmethod
    async def resolve(self, identity: AuthIdentity, now: datetime) -> AuthIdentity | None:
        raise NotImplementedError

    @abstractmethod
    async def has_device(self, device_hash: str, now: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def revoke_session(self, identity: AuthIdentity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def forget_device(self, device_hash: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_authorization(self, user_id: int, expected_grant: JiraUserGrant) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reconcile_privacy(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError


class JiraLoginPort(JiraUserGrantAccessPort):
    @abstractmethod
    async def finish_login(
        self, grant: JiraUserGrant, registered_identity: AuthIdentity, remember_token: str | None = None,
    ) -> tuple[AuthIdentity, str]:
        raise NotImplementedError

    @abstractmethod
    async def resume(self, cookie: str) -> AuthIdentity:
        raise NotImplementedError

    @abstractmethod
    async def resolve(self, identity: AuthIdentity) -> AuthIdentity:
        raise NotImplementedError

    @abstractmethod
    async def forget(self, cookie: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def has_device(self, cookie: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def reconcile_privacy(self) -> None:
        raise NotImplementedError
