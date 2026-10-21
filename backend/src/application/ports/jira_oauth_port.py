# backend/src/application/ports/jira_oauth_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.domain.entities.auth_identity import AuthIdentity


class JiraLoginDenied(ValueError):
    pass


class JiraLoginUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class JiraReportingGrant:
    identity: AuthIdentity
    refresh_token: str = field(repr=False)


@dataclass(frozen=True)
class JiraPersistentGrant:
    identity: AuthIdentity
    grant: JiraUserGrant


class JiraOAuthPort(ABC):
    @abstractmethod
    def authorization_url(self, state: str, include_offline: bool = False) -> str: ...

    @abstractmethod
    async def authenticate(self, code: str) -> AuthIdentity: ...

    @abstractmethod
    async def authenticate_reporting_owner(self, code: str) -> JiraReportingGrant: ...

    async def authenticate_persistent(self, code: str) -> JiraPersistentGrant:
        raise JiraLoginUnavailable("Persistent Jira login is unavailable")

    async def refresh_user_grant(self, grant: JiraUserGrant) -> JiraUserGrant:
        raise JiraLoginUnavailable("Persistent Jira login is unavailable")

    async def validate_user_grant(self, grant: JiraUserGrant) -> AuthIdentity:
        raise JiraLoginUnavailable("Persistent Jira login is unavailable")
