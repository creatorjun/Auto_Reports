# backend/src/infrastructure/cache/c_level_preview_cache.py
from collections import OrderedDict
from copy import deepcopy
from secrets import token_urlsafe
from time import monotonic
from typing import Any

from src.application.ports.c_level_repository import CLevelPreviewPort


class CLevelPreviewCache(CLevelPreviewPort):
    def __init__(self, maxsize: int = 16, ttl_seconds: float = 3600) -> None:
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._entries: OrderedDict[str, tuple[str, float, dict[str, Any]]] = OrderedDict()

    def _expire(self) -> None:
        now = monotonic()
        for key in list(self._entries):
            if self._entries[key][1] <= now:
                del self._entries[key]

    def put(self, payload: dict[str, Any], actor: str) -> str:
        self._expire()
        token = token_urlsafe(32)
        self._entries[token] = (actor, monotonic() + self._ttl, deepcopy(payload))
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)
        return token

    def get(self, token: str, actor: str) -> dict[str, Any] | None:
        self._expire()
        entry = self._entries.get(token)
        if entry is None or entry[0] != actor:
            return None
        self._entries.move_to_end(token)
        return deepcopy(entry[2])

    def replace(self, token: str, payload: dict[str, Any], actor: str) -> bool:
        self._expire()
        entry = self._entries.get(token)
        if entry is None or entry[0] != actor:
            return False
        self._entries[token] = (actor, entry[1], deepcopy(payload))
        return True

    async def aclose(self) -> None:
        self._entries.clear()
