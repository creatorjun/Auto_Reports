# backend/src/application/ports/sla_digest_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.sla_digest import SlaDigestEntry


class SlaDigestSourcePort(ABC):
    @abstractmethod
    async def fetch_entries(self) -> tuple[SlaDigestEntry, ...]:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError


class SlaDigestRendererPort(ABC):
    @abstractmethod
    def render(
        self, entries: tuple[SlaDigestEntry, ...], jira_base_url: str, now: datetime,
    ) -> str:
        raise NotImplementedError
