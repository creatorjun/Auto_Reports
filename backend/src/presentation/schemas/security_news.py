# backend/src/presentation/schemas/security_news.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.entities.security_news import NewsKind, NewsSeverity, NewsSourceStatus


class SecurityCveRemediationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: str
    affected_versions: str
    vendor: str | None = None
    fixed_version: str | None = None
    reference_url: str | None = None


class SecurityNewsItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    kind: NewsKind
    title: str
    summary: str
    url: str
    published_at: datetime | None
    updated_at: datetime | None
    cve_ids: tuple[str, ...]
    severity: NewsSeverity
    cvss_score: float | None
    cvss_version: str | None
    known_exploited: bool
    vendor: str | None
    product: str | None
    due_date: str | None
    title_ko: str | None = None
    summary_ko: str | None = None
    remediations: tuple[SecurityCveRemediationResponse, ...] = ()


class SecurityNewsSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    homepage: str
    kind: NewsKind
    status: NewsSourceStatus
    count: int
    last_success_at: datetime | None
    error: str | None
    warning: str | None = None


class SecurityNewsTranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool = False
    translating: bool = False
    translated_count: int = 0
    pending_count: int = 0
    message: str | None = None


class SecurityNewsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: tuple[SecurityNewsItemResponse, ...]
    sources: tuple[SecurityNewsSourceResponse, ...]
    initialized: bool
    refreshing: bool
    refreshed_at: datetime | None
    next_refresh_at: datetime | None
    refresh_interval_seconds: int
    retry_after_seconds: int = 0
    translation: SecurityNewsTranslationResponse = SecurityNewsTranslationResponse()
