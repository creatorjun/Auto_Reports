# backend/src/application/use_cases/security_news.py
import asyncio
import logging
import math
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from src.application.ports.security_news_port import SecurityNewsPort
from src.application.ports.security_news_snapshot_port import SecurityNewsSnapshotPort
from src.application.services.security_news_translation import SecurityNewsTranslationService
from src.domain.constants import KST
from src.domain.entities.security_news_translation import NewsTranslationState
from src.domain.entities.security_news import (
    SecurityNewsItem,
    SecurityNewsSnapshot,
    SecurityNewsSource,
    SecurityNewsSourceResult,
    SecurityNewsSourceState,
    SecurityNewsStoredSnapshot,
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
        manual_interval_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
        translation: SecurityNewsTranslationService | None = None,
        store: SecurityNewsSnapshotPort | None = None,
    ) -> None:
        self._source = source
        self._translation = translation
        self._store = store
        self._manual_interval = max(60, manual_interval_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._states = {
            source.id: SecurityNewsSourceState(
                id=source.id, name=source.name, homepage=source.homepage, kind=source.kind,
            )
            for source in self._source.sources
        }
        self._results: dict[str, SecurityNewsSourceResult] = {}
        self._rendered_items: tuple[SecurityNewsItem, ...] | None = None
        self._source_attempts: dict[str, datetime] = {}
        self._task: asyncio.Task[None] | None = None
        self._last_attempt: datetime | None = None
        self._refreshed_at: datetime | None = None
        self._initialized = False
        self._loaded = False
        self._lock = asyncio.Lock()
        self._last_scheduled_day: date | None = None
        self._closed = False

    async def initialize(self) -> None:
        async with self._lock:
            self._ensure_open()
            if self._loaded:
                return
            if self._store is not None:
                try:
                    saved = await self._store.load()
                    if saved is not None:
                        self._results = {key: result for key, result in saved.results if key in self._states}
                        self._rendered_items = None
                        self._source_attempts = {key: value for key, value in saved.source_attempts if key in self._states}
                        for state in saved.sources:
                            if state.id in self._states:
                                current = self._states[state.id]
                                self._states[state.id] = replace(
                                    state, name=current.name, homepage=current.homepage, kind=current.kind,
                                )
                        self._last_attempt = saved.last_attempt
                        self._refreshed_at = saved.refreshed_at
                        self._initialized = saved.initialized
                except Exception as error:
                    logger.warning("Security news snapshot restore failed: %s", type(error).__name__)
            if self._translation is not None:
                await self._translation.restore(tuple(
                    item for result in self._results.values() for item in result.items
                ))
            self._loaded = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Security news service is closed")

    def _running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def get_snapshot(self, *, refresh: bool = False) -> SecurityNewsSnapshot:
        await self.initialize()
        async with self._lock:
            self._ensure_open()
            if refresh and not self._running():
                now = self._clock()
                elapsed = (now - self._last_attempt).total_seconds() if self._last_attempt is not None else float("inf")
                if elapsed < self._manual_interval:
                    raise SecurityNewsRefreshThrottled(math.ceil(self._manual_interval - elapsed))
                self._start_refresh(now)
        now = self._clock()
        elapsed = (
            (now - self._last_attempt).total_seconds()
            if self._last_attempt is not None
            else float("inf")
        )
        rendered = self._items()
        translation_state = NewsTranslationState()
        if self._translation is not None:
            rendered, translation_state = self._translation.snapshot(rendered, start=False)
        return SecurityNewsSnapshot(
            items=rendered,
            sources=tuple(self._states.values()),
            initialized=self._initialized,
            refreshing=self._running(),
            refreshed_at=self._refreshed_at,
            next_refresh_at=(
                self._last_attempt + timedelta(seconds=self._manual_interval)
                if self._last_attempt is not None else None
            ),
            refresh_interval_seconds=86400,
            retry_after_seconds=max(0, math.ceil(self._manual_interval - elapsed)) if math.isfinite(elapsed) else 0,
            translation=translation_state,
        )

    def _items(self) -> tuple[SecurityNewsItem, ...]:
        if self._rendered_items is None:
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
            self._rendered_items = tuple(sorted(
                items.values(),
                key=lambda item: (item.published_at or item.updated_at or oldest, item.id),
                reverse=True,
            ))
        return self._rendered_items

    def _start_refresh(self, now: datetime) -> None:
        self._last_attempt = now
        self._task = asyncio.create_task(self._refresh(), name="security-news-refresh")

    async def refresh_scheduled(self) -> None:
        await self.initialize()
        async with self._lock:
            self._ensure_open()
            now = self._clock()
            day = now.astimezone(KST).date()
            if self._last_scheduled_day is not None and day <= self._last_scheduled_day:
                return
            if self._store is not None:
                try:
                    claimed = await self._store.claim_daily_refresh(day)
                except Exception as error:
                    logger.warning("Security news daily collection reservation failed: %s", type(error).__name__)
                    return
                if not claimed:
                    self._last_scheduled_day = day
                    return
            self._last_scheduled_day = day
            if not self._running():
                elapsed = (now - self._last_attempt).total_seconds() if self._last_attempt is not None else float("inf")
                if elapsed < self._manual_interval:
                    return
                self._start_refresh(now)
            task = self._task
        if task is not None:
            await asyncio.shield(task)

    async def _persist(self) -> None:
        if self._store is None:
            return
        try:
            await self._store.save(SecurityNewsStoredSnapshot(
                results=tuple(self._results.items()), sources=tuple(self._states.values()),
                source_attempts=tuple(self._source_attempts.items()), last_attempt=self._last_attempt,
                refreshed_at=self._refreshed_at, initialized=self._initialized,
            ))
        except Exception as error:
            logger.warning("Security news snapshot save failed: %s", type(error).__name__)

    async def _refresh(self) -> None:
        now = self._clock()
        sources = tuple(
            source for source in self._source.sources
            if source.id not in self._source_attempts
            or (now - self._source_attempts[source.id]).total_seconds() >= source.minimum_refresh_seconds
        )
        for source in sources:
            self._source_attempts[source.id] = now
        await self._persist()
        try:
            await asyncio.gather(*(self._refresh_source(source) for source in sources))
            self._initialized = True
            self._refreshed_at = self._clock()
        finally:
            await self._persist()
        if self._translation is not None:
            self._translation.snapshot(tuple(
                item for result in self._results.values() for item in result.items
            ))

    async def _refresh_source(self, source: SecurityNewsSource) -> None:
        state = self._states[source.id]
        try:
            result = await self._source.fetch(source.id)
            self._results[source.id] = result
            self._rendered_items = None
            self._states[source.id] = replace(
                state, status="ok", count=len({item.id for item in result.items}),
                last_success_at=self._clock(), error=None, warning=result.warning,
            )
        except Exception as error:
            logger.warning("Security news source %s failed: %s", source.id, type(error).__name__)
            self._states[source.id] = replace(
                state,
                status="stale" if state.last_success_at is not None else "error",
                error="출처에서 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.",
            )

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
