# backend/src/application/use_cases/get_report.py
from typing import Optional

from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository


class GetReportUseCase:
    def __init__(self, repository: ReportRepository):
        self._repository = repository

    async def get_latest(self) -> Optional[Report]:
        return await self._repository.find_latest()

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        return await self._repository.find_by_id(report_id)

    async def get_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        return await self._repository.find_all(limit=limit, offset=offset)

    async def delete(self, report_id: int) -> bool:
        return await self._repository.delete(report_id)
