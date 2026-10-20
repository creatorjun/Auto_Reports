# backend/src/domain/entities/security_news.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.domain.entities.security_news_translation import NewsTranslationState


NewsKind = Literal["cve", "advisory", "news"]
NewsSeverity = Literal["critical", "high", "medium", "low", "unknown"]
NewsSourceStatus = Literal["ok", "stale", "error", "pending"]


@dataclass(frozen=True)
class SecurityNewsItem:
    id: str
    source_id: str
    kind: NewsKind
    title: str
    summary: str
    url: str
    published_at: datetime | None = None
    updated_at: datetime | None = None
    cve_ids: tuple[str, ...] = ()
    severity: NewsSeverity = "unknown"
    cvss_score: float | None = None
    cvss_version: str | None = None
    known_exploited: bool = False
    vendor: str | None = None
    product: str | None = None
    due_date: str | None = None
    title_ko: str | None = None
    summary_ko: str | None = None


@dataclass(frozen=True)
class SecurityNewsSource:
    id: str
    name: str
    homepage: str
    kind: NewsKind
    minimum_refresh_seconds: int = 0


@dataclass(frozen=True)
class SecurityNewsSourceResult:
    items: tuple[SecurityNewsItem, ...]
    known_exploited_cve_ids: frozenset[str] = frozenset()
    warning: str | None = None


@dataclass(frozen=True)
class SecurityNewsSourceState:
    id: str
    name: str
    homepage: str
    kind: NewsKind
    status: NewsSourceStatus = "pending"
    count: int = 0
    last_success_at: datetime | None = None
    error: str | None = None
    warning: str | None = None


@dataclass(frozen=True)
class SecurityNewsSnapshot:
    items: tuple[SecurityNewsItem, ...]
    sources: tuple[SecurityNewsSourceState, ...]
    initialized: bool
    refreshing: bool
    refreshed_at: datetime | None
    next_refresh_at: datetime | None
    refresh_interval_seconds: int
    retry_after_seconds: int = 0
    translation: NewsTranslationState = NewsTranslationState()
