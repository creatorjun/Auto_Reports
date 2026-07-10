# backend/src/shared/cache.py
import asyncio
import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")

_LATEST_KEY = "__latest__"
_PURGE_INTERVAL = 60.0


class LruCache(Generic[K, V]):
    def __init__(self, maxsize: int = 32, ttl_seconds: float = 300.0):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._last_purge: float = time.monotonic()
        self._lock = asyncio.Lock()

    def get(self, key: K) -> Optional[V]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        expires_at = time.monotonic() + self._ttl
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, expires_at)
        self._maybe_purge()
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    async def async_get(self, key: K) -> Optional[V]:
        async with self._lock:
            return self.get(key)

    async def async_set(self, key: K, value: V) -> None:
        async with self._lock:
            self.set(key, value)

    def get_latest_id(self) -> Optional[K]:
        entry = self._store.get(_LATEST_KEY)  # type: ignore[arg-type]
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[_LATEST_KEY]  # type: ignore[arg-type]
            return None
        return value  # type: ignore[return-value]

    def set_latest_id(self, key: Optional[K]) -> None:
        if key is None:
            self._store.pop(_LATEST_KEY, None)  # type: ignore[arg-type]
            return
        self._store[_LATEST_KEY] = (key, time.monotonic() + self._ttl)  # type: ignore[assignment]

    async def async_get_latest_id(self) -> Optional[K]:
        async with self._lock:
            return self.get_latest_id()

    async def async_set_latest_id(self, key: Optional[K]) -> None:
        async with self._lock:
            self.set_latest_id(key)

    def delete(self, key: K) -> None:
        self._store.pop(key, None)

    async def async_delete(self, key: K) -> None:
        async with self._lock:
            self.delete(key)

    def invalidate_all(self) -> None:
        self._store.clear()

    async def async_invalidate_all(self) -> None:
        async with self._lock:
            self.invalidate_all()

    def _maybe_purge(self) -> None:
        now = time.monotonic()
        if now - self._last_purge < _PURGE_INTERVAL:
            return
        expired = [k for k, (_, exp) in self._store.items() if exp < now]
        for k in expired:
            del self._store[k]
        self._last_purge = now

    def __len__(self) -> int:
        return len(self._store)
