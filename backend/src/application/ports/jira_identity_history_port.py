# backend/src/application/ports/jira_identity_history_port.py
from abc import ABC, abstractmethod

from src.domain.entities.jira_identity_history import JiraIdentityHistory


class JiraIdentityHistoryUnavailable(RuntimeError):
    pass


class JiraIdentityHistoryPort(ABC):
    @abstractmethod
    async def fetch(self, issue_key: str) -> JiraIdentityHistory: ...
