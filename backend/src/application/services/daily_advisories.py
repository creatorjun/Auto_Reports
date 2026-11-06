# backend/src/application/services/daily_advisories.py
import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Generic, Protocol, TypeVar
from uuid import uuid4

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.domain.constants import KST
from src.domain.entities.advisory_feed import AdvisorySnapshot, AdvisoryStatus, DataT


logger = logging.getLogger(__name__)


class Feed(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def url(self) -> str: ...


FeedT = TypeVar("FeedT", bound=Feed)
FeedCo = TypeVar("FeedCo", bound=Feed, covariant=True)


class Target(Protocol[FeedCo]):
    @property
    def id(self) -> str: ...

    @property
    def available(self) -> bool: ...

    @property
    def feeds(self) -> tuple[FeedCo, ...]: ...


TargetT = TypeVar("TargetT", bound=Target)


def scheduled_day(now: datetime) -> date:
    return (now.astimezone(KST) - timedelta(hours=8)).date()


@dataclass(frozen=True)
class AdvisorySourceState:
    id: str
    label: str
    url: str
    status: AdvisoryStatus
    refreshed_at: datetime | None
    note: str | None


@dataclass(frozen=True)
class AdvisoryCoverage:
    status: AdvisoryStatus
    refreshing: bool
    sources: tuple[AdvisorySourceState, ...]
    coverage_note: str | None


@dataclass
class FeedCache(Generic[DataT]):
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    loaded: bool = False
    snapshot: AdvisorySnapshot[DataT] | None = None
    task: asyncio.Task | None = None
    failure: str | None = None
    attempted_day: date | None = None


class DailyAdvisories(Generic[TargetT, FeedT, DataT]):
    def __init__(
        self, targets: tuple[TargetT, ...], fetch: Callable[[TargetT, FeedT], Awaitable[DataT]],
        store: AdvisorySnapshotPort[DataT], clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._feeds_targets = targets
        self._fetch = fetch
        self._store = store
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._cache: dict[tuple[str, str], FeedCache[DataT]] = {}
        self._slots = asyncio.Semaphore(1)
        self._closed = False

    async def _restore(self, target: TargetT, feed: FeedT, entry: FeedCache[DataT]) -> None:
        history = await self._store.load(target.id, feed.id)
        entry.snapshot = history.snapshot
        entry.attempted_day = history.completed_day
        entry.failure = history.error

    async def _refresh(self, target: TargetT, feed: FeedT, entry: FeedCache[DataT], day: date) -> None:
        owner = uuid4().hex
        try:
            while True:
                async with self._slots:
                    if scheduled_day(self._clock()) != day:
                        return
                    claim = await self._store.claim(target.id, feed.id, day, owner, self._clock())
                    if claim.acquired:
                        await self._collect(target, feed, entry, owner)
                        return
                    if claim.lease_until is None:
                        await self._restore(target, feed, entry)
                        return
                await asyncio.sleep(max(0.1, min(10, (claim.lease_until - self._clock()).total_seconds())))
        except asyncio.CancelledError:
            await self._store.abandon(target.id, feed.id, owner)
            raise
        except Exception:
            logger.warning("Advisory feed cache failed for %s/%s", target.id, feed.id, exc_info=True)
            entry.failure = "출처 자료를 저장하거나 복원하지 못했습니다."
        finally:
            entry.task = None

    async def _collect(self, target: TargetT, feed: FeedT, entry: FeedCache[DataT], owner: str) -> None:
        snapshot = None
        error = None
        try:
            async with asyncio.timeout(12 * 60):
                data = await self._fetch(target, feed)
            if not data.complete and entry.snapshot is not None and entry.snapshot.data.complete:
                error = data.note or "이번 수집이 불완전하여 직전 정상 자료를 표시합니다."
            else:
                snapshot = AdvisorySnapshot(data, self._clock())
        except Exception:
            logger.warning("Advisory feed refresh failed for %s/%s", target.id, feed.id, exc_info=True)
            error = "출처 자료를 갱신하지 못했습니다."
        if await self._store.finish(target.id, feed.id, owner, snapshot, error):
            if snapshot is not None:
                entry.snapshot = snapshot
            entry.failure = error
        else:
            await self._restore(target, feed, entry)

    async def _read_feed(self, target: TargetT, feed: FeedT):
        entry = self._cache.setdefault((target.id, feed.id), FeedCache())
        async with entry.lock:
            if not entry.loaded:
                try:
                    await self._restore(target, feed, entry)
                except Exception:
                    logger.warning("Advisory feed cache read failed for %s/%s", target.id, feed.id, exc_info=True)
                entry.loaded = True
            day = scheduled_day(self._clock())
            if entry.attempted_day != day and not self._closed and entry.task is None:
                entry.attempted_day = day
                entry.task = asyncio.create_task(self._refresh(target, feed, entry, day))
            snapshot = entry.snapshot
            if snapshot is None:
                status = "error" if entry.failure else "pending"
            elif entry.failure or scheduled_day(snapshot.refreshed_at) < day:
                status = "stale"
            else:
                status = "ready" if snapshot.data.complete else "partial"
            note = entry.failure or (snapshot.data.note if snapshot else None)
            state = AdvisorySourceState(feed.id, feed.label, feed.url, status, snapshot.refreshed_at if snapshot else None, note or None)
            return state, snapshot, entry.task is not None

    async def refresh_scheduled(self) -> None:
        await self._refresh_targets(self._feeds_targets)

    async def _refresh_targets(self, targets: tuple[TargetT, ...]) -> None:
        while not self._closed:
            day = scheduled_day(self._clock())
            for target in targets:
                if target.available:
                    for feed in target.feeds:
                        await self._read_feed(target, feed)
            tasks = [entry.task for entry in self._cache.values() if entry.task is not None]
            await asyncio.gather(*tasks)
            if scheduled_day(self._clock()) == day:
                return

    async def read_coverage(self, target: TargetT, feeds: Iterable[FeedT]) -> tuple[AdvisoryCoverage, tuple[DataT, ...]]:
        values = await asyncio.gather(*(self._read_feed(target, feed) for feed in feeds))
        sources = tuple(state for state, _, _ in values)
        data = tuple(snapshot.data for _, snapshot, _ in values if snapshot is not None)
        statuses = {source.status for source in sources}
        if not data:
            status = "pending" if "pending" in statuses else "error"
        elif statuses == {"ready"}:
            status = "ready"
        elif statuses == {"stale"}:
            status = "stale"
        else:
            status = "partial"
        return AdvisoryCoverage(status, any(running for _, _, running in values), sources, None), data

    async def aclose(self) -> None:
        self._closed = True
        tasks = [entry.task for entry in self._cache.values() if entry.task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
