# backend/src/domain/entities/security_news_translation.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsTranslationInput:
    key: str
    title: str
    summary: str


@dataclass(frozen=True)
class NewsTranslation:
    key: str
    title_ko: str
    summary_ko: str


@dataclass(frozen=True)
class NewsTranslationReservation:
    inputs: tuple[NewsTranslationInput, ...] = ()
    next_attempt_at: datetime | None = None
    message: str | None = None


@dataclass(frozen=True)
class NewsTranslationState:
    enabled: bool = False
    translating: bool = False
    translated_count: int = 0
    pending_count: int = 0
    message: str | None = None
