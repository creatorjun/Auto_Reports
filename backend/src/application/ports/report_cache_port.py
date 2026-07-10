# backend/src/application/ports/report_cache_port.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.report import Report


class ReportCachePort(ABC):
    @abstractmethod
    async def get(self, report_id: int) -> Optional[Report]: ...

    @abstractmethod
    async def set(self, report_id: int, report: Report) -> None: ...

    @abstractmethod
    async def get_latest_id(self) -> Optional[int]: ...

    @abstractmethod
    async def set_latest_id(self, report_id: Optional[int]) -> None: ...

    @abstractmethod
    async def delete(self, report_id: int) -> None: ...
