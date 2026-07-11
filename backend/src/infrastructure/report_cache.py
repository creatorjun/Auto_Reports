# backend/src/infrastructure/report_cache.py
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.domain.entities.report import Report
from src.shared.cache import LruCache


class ReportLruCache(ReportCachePort):
    def __init__(self, maxsize: int = 50, ttl_seconds: float = 600.0):
        self._cache: LruCache[int, Report] = LruCache(maxsize=maxsize, ttl_seconds=ttl_seconds)

    async def get(self, report_id: int) -> Optional[Report]:
        return await self._cache.async_get(report_id)

    async def set(self, report_id: int, report: Report) -> None:
        await self._cache.async_set(report_id, report)

    async def get_latest_id(self) -> Optional[int]:
        return await self._cache.async_get_latest_id()

    async def set_latest_id(self, report_id: Optional[int]) -> None:
        await self._cache.async_set_latest_id(report_id)

    async def delete(self, report_id: int) -> None:
        await self._cache.async_delete(report_id)
