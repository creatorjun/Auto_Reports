# backend/src/shared/cache.py
import time
from collections import OrderedDict
from typing import Any, Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LruCache(Generic[K, V]):
    def __init__(self, maxsize: int = 32, ttl_seconds: float = 300.0):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._store: OrderedDict[K, tuple[V, float]] = OrderedDict()

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
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def delete(self, key: K) -> None:
        self._store.pop(key, None)

    def invalidate_all(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
