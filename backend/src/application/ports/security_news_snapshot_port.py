# backend/src/application/ports/security_news_snapshot_port.py
from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.security_news import SecurityNewsStoredSnapshot


class SecurityNewsSnapshotPort(ABC):
    @abstractmethod
    async def load(self) -> SecurityNewsStoredSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, snapshot: SecurityNewsStoredSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def claim_daily_refresh(self, day: date) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
