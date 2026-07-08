# backend/src/domain/repositories/report_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.report import NewReport, Report


class ReportRepository(ABC):
    @abstractmethod
    async def save(self, report: NewReport) -> Report: ...

    @abstractmethod
    async def find_by_id(self, report_id: int) -> Optional[Report]: ...

    @abstractmethod
    async def find_latest(self) -> Optional[Report]: ...

    @abstractmethod
    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Report]: ...

    @abstractmethod
    async def delete(self, report_id: int) -> bool: ...
