# backend/src/application/use_cases/security_news.py
import asyncio
import logging
import math
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.application.ports.security_news_port import SecurityNewsPort
from src.application.services.security_news_translation import SecurityNewsTranslationService
from src.domain.entities.security_news_translation import NewsTranslationState
from src.domain.entities.security_news import (
    SecurityNewsSnapshot,
    SecurityNewsSource,
    SecurityNewsSourceResult,
    SecurityNewsSourceState,
)


logger = logging.getLogger(__name__)


class SecurityNewsRefreshThrottled(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("보안 뉴스는 60초에 한 번 새로고침할 수 있습니다.")


class SecurityNewsUseCase:
    def __init__(
        self,
        source: SecurityNewsPort,
        *,
        refresh_interval_seconds: int = 900,
        manual_interval_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
        translation: SecurityNewsTranslationService | None = None,
    ) -> None:
        self._source = source
        self._translation = translation
        self._interval = max(60, refresh_interval_seconds)
        self._manual_interval = max(60, manual_interval_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._states = {
            source.id: SecurityNewsSourceState(
                id=source.id, name=source.name, homepage=source.homepage, kind=source.kind,
            )
            for source in self._source.sources
        }
        self._results: dict[str, SecurityNewsSourceResult] = {}
        self._source_attempts: dict[str, datetime] = {}
        self._task: asyncio.Task[None] | None = None
        self._last_attempt: datetime | None = None
        self._refreshed_at: datetime | None = None
        self._initialized = False
        self._closed = False

    async def get_snapshot(self, *, refresh: bool = False) -> SecurityNewsSnapshot:
        if self._closed:
            raise RuntimeError("Security news service is closed")
        now = self._clock()
        running = self._task is not None and not self._task.done()
        elapsed = (
            (now - self._last_attempt).total_seconds()
            if self._last_attempt is not None
            else float("inf")
        )
        if refresh and not running and elapsed < self._manual_interval:
            raise SecurityNewsRefreshThrottled(math.ceil(self._manual_interval - elapsed))
        if not running and (refresh or elapsed >= self._interval):
            self._last_attempt = now
            elapsed = 0
            self._task = asyncio.create_task(self._refresh(), name="security-news-refresh")
            running = True
        exploited = frozenset().union(
            *(result.known_exploited_cve_ids for result in self._results.values())
        )
        items = {
            (item.source_id, item.id): replace(
                item,
                known_exploited=item.known_exploited or bool(exploited.intersection(item.cve_ids)),
            )
            for result in self._results.values()
            for item in result.items
        }
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        rendered = tuple(sorted(
            items.values(),
            key=lambda item: (item.published_at or item.updated_at or oldest, item.id),
            reverse=True,
        ))
        translation_state = NewsTranslationState()
        if self._translation is not None:
            rendered, translation_state = self._translation.snapshot(rendered)
        return SecurityNewsSnapshot(
            items=rendered,
            sources=tuple(self._states.values()),
            initialized=self._initialized,
            refreshing=running,
            refreshed_at=self._refreshed_at,
            next_refresh_at=(
                self._last_attempt + timedelta(seconds=self._manual_interval)
                if self._last_attempt is not None else None
            ),
            refresh_interval_seconds=self._interval,
            retry_after_seconds=max(0, math.ceil(self._manual_interval - elapsed)) if math.isfinite(elapsed) else 0,
            translation=translation_state,
        )

    async def _refresh(self) -> None:
        await asyncio.gather(*(self._refresh_source(source) for source in self._source.sources))
        self._initialized = True
        self._refreshed_at = self._clock()

    async def _refresh_source(self, source: SecurityNewsSource) -> None:
        now = self._clock()
        previous_attempt = self._source_attempts.get(source.id)
        if previous_attempt is not None and (now - previous_attempt).total_seconds() < source.minimum_refresh_seconds:
            return
        self._source_attempts[source.id] = now
        state = self._states[source.id]
        try:
            result = await self._source.fetch(source.id)
            self._results[source.id] = result
            self._states[source.id] = replace(
                state, status="ok", count=len({item.id for item in result.items}),
                last_success_at=self._clock(), error=None, warning=result.warning,
            )
            if self._translation is not None:
                self._translation.snapshot(tuple(
                    item for cached in self._results.values() for item in cached.items
                ))
        except Exception as error:
            logger.warning("Security news source %s failed: %s", source.id, type(error).__name__)
            self._states[source.id] = replace(
                state,
                status="stale" if state.last_success_at is not None else "error",
                error="출처에서 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.",
            )

    async def aclose(self) -> None:
        self._closed = True
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
