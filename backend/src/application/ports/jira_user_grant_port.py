# backend/src/application/ports/jira_user_grant_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.auth_identity import AuthIdentity


@dataclass(frozen=True)
class JiraUserGrant:
    cloud_id: str
    account_id: str
    access_token: str = field(repr=False)
    expires_at: datetime
    refresh_token: str | None = field(default=None, repr=False)


class JiraUserGrantAccessPort(ABC):
    @abstractmethod
    async def get(self, grant_id: str, identity: AuthIdentity) -> JiraUserGrant | None:
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, grant_id: str, identity: AuthIdentity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError


class JiraUserGrantStorePort(JiraUserGrantAccessPort):
    @abstractmethod
    async def put(self, grant: JiraUserGrant, identity: AuthIdentity) -> str:
        raise NotImplementedError
