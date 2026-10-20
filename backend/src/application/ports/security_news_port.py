# backend/src/application/ports/security_news_port.py
from abc import ABC, abstractmethod

from src.domain.entities.security_news import SecurityNewsSource, SecurityNewsSourceResult


class SecurityNewsPort(ABC):
    @property
    @abstractmethod
    def sources(self) -> tuple[SecurityNewsSource, ...]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, source_id: str) -> SecurityNewsSourceResult:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
