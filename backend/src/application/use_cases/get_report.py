# backend/src/application/use_cases/get_report.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository
from src.shared.cache import LruCache

logger = logging.getLogger(__name__)


class GetReportUseCase:
    def __init__(self, repository: ReportRepository, cache: LruCache):
        self._repository = repository
        self._cache = cache

    async def get_latest(self) -> Optional[Report]:
        latest_id = self._cache.get_latest_id()
        if latest_id is not None:
            cached = self._cache.get(latest_id)
            if cached is not None:
                logger.debug("캐시 HIT: latest report")
                return cached
        report = await self._repository.find_latest()
        if report is not None:
            self._cache.set(report.id, report)
            self._cache.set_latest_id(report.id)
        return report

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        cached = self._cache.get(report_id)
        if cached is not None:
            logger.debug(f"캐시 HIT: report_id={report_id}")
            return cached
        report = await self._repository.find_by_id(report_id)
        if report is not None:
            self._cache.set(report_id, report)
        return report

    async def get_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        return await self._repository.find_all(limit=limit, offset=offset)

    async def delete(self, report_id: int) -> bool:
        deleted = await self._repository.delete(report_id)
        if deleted:
            self._cache.delete(report_id)
            latest_id = self._cache.get_latest_id()
            if latest_id == report_id:
                self._cache.set_latest_id(None)
        return deleted
