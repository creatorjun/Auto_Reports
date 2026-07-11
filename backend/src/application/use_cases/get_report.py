# backend/src/application/use_cases/get_report.py
import logging
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository

logger = logging.getLogger(__name__)


class GetReportUseCase:
    def __init__(self, repository: ReportRepository, cache: ReportCachePort):
        self._repository = repository
        self._cache = cache

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        cached = await self._cache.get(
            report_id,
            refresh_fn=self._fetch_by_id,
        )
        if cached is not None:
            return cached
        report = await self._repository.find_by_id(report_id)
        if report:
            await self._cache.set(report.id, report)
        return report

    async def get_latest(self) -> Optional[Report]:
        latest_id = await self._cache.get_latest_id()
        if latest_id is not None:
            cached = await self._cache.get(
                latest_id,
                refresh_fn=self._fetch_by_id,
            )
            if cached is not None:
                return cached

        report = await self._repository.find_latest()
        if report:
            await self._cache.set(report.id, report)
            await self._cache.set_latest_id(report.id)
        return report

    async def get_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        return await self._repository.find_all(limit=limit, offset=offset)

    async def list_all(self) -> list[Report]:
        return await self._repository.find_all()

    async def delete(self, report_id: int) -> bool:
        deleted = await self._repository.delete(report_id)
        if deleted:
            await self._cache.delete(report_id)
            latest_id = await self._cache.get_latest_id()
            if latest_id == report_id:
                await self._cache.set_latest_id(None)
        return deleted

    async def _fetch_by_id(self, report_id: int) -> Optional[Report]:
        try:
            return await self._repository.find_by_id(report_id)
        except Exception as exc:
            logger.error(f"[cache-refresh] DB 조회 실패: id={report_id} -> {exc}")
            return None
