# backend/src/infrastructure/report_cache.py
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.domain.entities.report import Report
from src.shared.cache import LruCache


class ReportLruCache(LruCache[int, Report], ReportCachePort):
    async def get(self, report_id: int) -> Optional[Report]:
        return await self.async_get(report_id)

    async def set(self, report_id: int, report: Report) -> None:
        await self.async_set(report_id, report)

    async def get_latest_id(self) -> Optional[int]:
        return await self.async_get_latest_id()

    async def set_latest_id(self, report_id: Optional[int]) -> None:
        await self.async_set_latest_id(report_id)

    async def delete(self, report_id: int) -> None:
        await self.async_delete(report_id)
