# backend/src/application/use_cases/get_report.py
from typing import Optional

from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository
from src.shared.cache import LruCache


class GetReportUseCase:
    def __init__(self, repository: ReportRepository, cache: LruCache):
        self._repository = repository
        self._cache = cache

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        cached = await self._cache.async_get(report_id)
        if cached is not None:
            return cached
        report = await self._repository.find_by_id(report_id)
        if report:
            await self._cache.async_set(report_id, report)
        return report

    async def get_latest(self) -> Optional[Report]:
        latest_id = await self._cache.async_get_latest_id()
        if latest_id is not None:
            cached = await self._cache.async_get(latest_id)
            if cached is not None:
                return cached
        report = await self._repository.find_latest()
        if report:
            await self._cache.async_set(report.id, report)
            await self._cache.async_set_latest_id(report.id)
        return report

    async def get_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        return await self._repository.find_all(limit=limit, offset=offset)

    async def list_all(self) -> list[Report]:
        return await self._repository.find_all()

    async def delete(self, report_id: int) -> bool:
        deleted = await self._repository.delete(report_id)
        if deleted:
            await self._cache.async_delete(report_id)
            latest_id = await self._cache.async_get_latest_id()
            if latest_id == report_id:
                await self._cache.async_set_latest_id(None)
        return deleted
