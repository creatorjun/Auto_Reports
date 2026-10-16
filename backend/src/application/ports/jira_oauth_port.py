# backend/src/application/ports/jira_oauth_port.py
from abc import ABC, abstractmethod

from src.domain.entities.auth_identity import AuthIdentity


class JiraLoginDenied(ValueError):
    pass


class JiraLoginUnavailable(RuntimeError):
    pass


class JiraOAuthPort(ABC):
    @abstractmethod
    def authorization_url(self, state: str) -> str: ...

    @abstractmethod
    async def authenticate(self, code: str) -> AuthIdentity: ...
