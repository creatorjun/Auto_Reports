# backend/src/application/ports/report_repository.py
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from src.domain.entities.report import NewReport, Report, ReportSummary


class ReportRepository(ABC):
    @abstractmethod
    async def save(self, report: NewReport) -> Report: ...

    @abstractmethod
    async def find_by_id(self, report_id: int) -> Optional[Report]: ...

    @abstractmethod
    async def find_latest(self) -> Optional[Report]: ...

    @abstractmethod
    async def find_annual(self, year: int) -> Optional[Report]: ...

    @abstractmethod
    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Report]: ...

    async def find_summaries(self, limit: int = 20, offset: int = 0) -> list[ReportSummary]:
        reports = await self.find_all(limit=limit, offset=offset)
        return [ReportSummary(
            id=report.id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            created_at=report.created_at,
            sentiment=report.ai_analysis.sentiment if report.ai_analysis else None,
            scope=report.scope,
            report_year=report.report_year,
        ) for report in reports]

    @abstractmethod
    async def delete(self, report_id: int) -> bool: ...

    @abstractmethod
    async def delete_before(self, cutoff: date) -> list[int]: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def update_widgets(self, report_id: int, report: NewReport) -> Report: ...
