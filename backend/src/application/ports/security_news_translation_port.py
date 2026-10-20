# backend/src/application/ports/security_news_translation_port.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from src.domain.entities.security_news_translation import (
    NewsTranslation,
    NewsTranslationInput,
    NewsTranslationReservation,
)


TranslationFailure = Literal["quota", "billing", "authorization", "provider", "invalid"]


class NewsTranslationProviderError(Exception):
    def __init__(self, reason: TranslationFailure = "provider") -> None:
        self.reason = reason
        super().__init__("Security news translation provider is unavailable")


class NewsTranslationPort(ABC):
    @abstractmethod
    async def translate(self, inputs: tuple[NewsTranslationInput, ...]) -> tuple[NewsTranslation, ...]:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError


class NewsTranslationCachePort(ABC):
    @abstractmethod
    async def read(self, keys: tuple[str, ...]) -> dict[str, NewsTranslation]:
        raise NotImplementedError

    @abstractmethod
    async def reserve(
        self,
        inputs: tuple[NewsTranslationInput, ...],
        *,
        now: datetime,
        daily_limit: int,
        batch_size: int,
        minimum_interval_seconds: float,
        max_attempts: int,
    ) -> NewsTranslationReservation:
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        inputs: tuple[NewsTranslationInput, ...],
        translations: tuple[NewsTranslation, ...],
        *,
        now: datetime,
        failure: TranslationFailure | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
