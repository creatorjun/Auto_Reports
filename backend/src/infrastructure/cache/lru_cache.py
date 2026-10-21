# backend/src/infrastructure/cache/lru_cache.py
import asyncio
import logging
import time
from collections import OrderedDict
from typing import Awaitable, Callable, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")

logger = logging.getLogger(__name__)

_LATEST_KEY = "__latest__"
_PURGE_INTERVAL = 60.0


class LruCache(Generic[K, V]):
    def __init__(
        self,
        maxsize: int = 32,
        ttl_seconds: float = 300.0,
        stale_ttl_seconds: float = 60.0,
    ):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._stale_ttl = stale_ttl_seconds
        self._store: OrderedDict[K, tuple[V, float, float]] = OrderedDict()
        self._last_purge: float = time.monotonic()
        self._lock = asyncio.Lock()
        self._refreshing: set[K] = set()
        self._inflight: dict[K, asyncio.Future] = {}
        self._tasks: set[asyncio.Task] = set()

    def _fresh_expires_at(self) -> float:
        return time.monotonic() + self._ttl

    def _stale_expires_at(self, fresh_expires_at: float) -> float:
        return fresh_expires_at + self._stale_ttl

    def get(self, key: K) -> Optional[V]:
        if key not in self._store:
            return None
        value, fresh_at, stale_at = self._store[key]
        now = time.monotonic()
        if now > stale_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def is_stale(self, key: K) -> bool:
        if key not in self._store:
            return False
        _, fresh_at, stale_at = self._store[key]
        now = time.monotonic()
        return now > fresh_at and now <= stale_at

    def set(self, key: K, value: V) -> None:
        fresh_at = self._fresh_expires_at()
        stale_at = self._stale_expires_at(fresh_at)
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, fresh_at, stale_at)
        self._maybe_purge()
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    async def async_get(
        self,
        key: K,
        refresh_fn: Optional[Callable[[K], Awaitable[Optional[V]]]] = None,
    ) -> Optional[V]:
        async with self._lock:
            value = self.get(key)
            if value is not None:
                if self.is_stale(key) and refresh_fn is not None and key not in self._inflight:
                    self._refreshing.add(key)
                    self._start_fetch(key, refresh_fn)
                return value
            if refresh_fn is None:
                return None
            task = self._inflight.get(key)
            if task is None:
                task = self._start_fetch(key, refresh_fn)
        return await asyncio.shield(task)

    def _start_fetch(self, key: K, refresh_fn: Callable[[K], Awaitable[Optional[V]]]) -> asyncio.Task:
        task = asyncio.create_task(self._fetch(key, refresh_fn), name=f"cache-refresh-{key}")
        self._inflight[key] = task
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _fetch(self, key: K, refresh_fn: Callable[[K], Awaitable[Optional[V]]]) -> Optional[V]:
        task = asyncio.current_task()
        try:
            value = await refresh_fn(key)
            async with self._lock:
                if self._inflight.get(key) is not task:
                    return None
                if value is not None:
                    self.set(key, value)
                return value
        except asyncio.CancelledError:
            if self._inflight.get(key) is not task:
                return None
            raise
        except Exception as error:
            logger.error("[cache] fetch failed: key=%s -> %s", key, error)
            return None
        finally:
            async with self._lock:
                if self._inflight.get(key) is task:
                    self._inflight.pop(key, None)
                    self._refreshing.discard(key)

    async def async_set(self, key: K, value: V) -> None:
        async with self._lock:
            self.set(key, value)

    def get_latest_id(self) -> Optional[K]:
        entry = self._store.get(_LATEST_KEY)
        if entry is None:
            return None
        value, fresh_at, stale_at = entry
        if time.monotonic() > stale_at:
            del self._store[_LATEST_KEY]
            return None
        return value

    def set_latest_id(self, key: Optional[K]) -> None:
        if key is None:
            self._store.pop(_LATEST_KEY, None)
            return
        fresh_at = self._fresh_expires_at()
        stale_at = self._stale_expires_at(fresh_at)
        self._store[_LATEST_KEY] = (key, fresh_at, stale_at)

    async def async_get_latest_id(self) -> Optional[K]:
        async with self._lock:
            return self.get_latest_id()

    async def async_set_latest_id(self, key: Optional[K]) -> None:
        async with self._lock:
            self.set_latest_id(key)

    def delete(self, key: K) -> None:
        self._store.pop(key, None)
        self._refreshing.discard(key)
        task = self._inflight.pop(key, None)
        if task is not None:
            task.cancel()

    async def async_delete(self, key: K) -> None:
        async with self._lock:
            self.delete(key)

    def invalidate_all(self) -> None:
        self._store.clear()
        self._refreshing.clear()
        tasks = tuple(self._inflight.values())
        self._inflight.clear()
        for task in tasks:
            task.cancel()

    async def async_invalidate_all(self) -> None:
        async with self._lock:
            self.invalidate_all()

    async def aclose(self) -> None:
        async with self._lock:
            tasks = tuple(self._tasks)
            self._tasks.clear()
            self.invalidate_all()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _maybe_purge(self) -> None:
        now = time.monotonic()
        if now - self._last_purge < _PURGE_INTERVAL:
            return
        expired = [k for k, (_, __, stale_at) in self._store.items() if stale_at < now]
        for k in expired:
            del self._store[k]
        self._last_purge = now

    def __len__(self) -> int:
        return len(self._store)
