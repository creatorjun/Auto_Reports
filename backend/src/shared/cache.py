# backend/src/shared/cache.py
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
            stale = self.is_stale(key)

        if value is None:
            return None

        if stale and refresh_fn is not None and key not in self._refreshing:
            self._refreshing.add(key)
            asyncio.get_event_loop().create_task(
                self._background_refresh(key, refresh_fn),
                name=f"cache-refresh-{key}",
            )
            logger.debug(f"[cache] stale 감지, 백그라운드 갱신 예약: key={key}")

        return value

    async def _background_refresh(self, key: K, refresh_fn: Callable[[K], Awaitable[Optional[V]]]) -> None:
        try:
            new_value = await refresh_fn(key)
            if new_value is not None:
                await self.async_set(key, new_value)
                logger.info(f"[cache] 백그라운드 새로고침 완료: key={key}")
            else:
                logger.warning(f"[cache] 백그라운드 새로고침 실패 (None 반환): key={key}")
        except Exception as exc:
            logger.error(f"[cache] 백그라운드 새로고침 오류: key={key} -> {exc}")
        finally:
            self._refreshing.discard(key)

    async def async_set(self, key: K, value: V) -> None:
        async with self._lock:
            self.set(key, value)

    def get_latest_id(self) -> Optional[K]:
        entry = self._store.get(_LATEST_KEY)  # type: ignore[arg-type]
        if entry is None:
            return None
        value, fresh_at, stale_at = entry
        if time.monotonic() > stale_at:
            del self._store[_LATEST_KEY]  # type: ignore[arg-type]
            return None
        return value  # type: ignore[return-value]

    def set_latest_id(self, key: Optional[K]) -> None:
        if key is None:
            self._store.pop(_LATEST_KEY, None)  # type: ignore[arg-type]
            return
        fresh_at = self._fresh_expires_at()
        stale_at = self._stale_expires_at(fresh_at)
        self._store[_LATEST_KEY] = (key, fresh_at, stale_at)  # type: ignore[assignment]

    async def async_get_latest_id(self) -> Optional[K]:
        async with self._lock:
            return self.get_latest_id()

    async def async_set_latest_id(self, key: Optional[K]) -> None:
        async with self._lock:
            self.set_latest_id(key)

    def delete(self, key: K) -> None:
        self._store.pop(key, None)
        self._refreshing.discard(key)

    async def async_delete(self, key: K) -> None:
        async with self._lock:
            self.delete(key)

    def invalidate_all(self) -> None:
        self._store.clear()
        self._refreshing.clear()

    async def async_invalidate_all(self) -> None:
        async with self._lock:
            self.invalidate_all()

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
