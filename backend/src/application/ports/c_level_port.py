# backend/src/application/ports/c_level_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.c_level_report import CLevelIssue


class CLevelSourcePort(ABC):
    @abstractmethod
    async def fetch_issues(
        self,
        earliest: datetime,
        as_of: datetime,
        refresh: bool = False,
    ) -> tuple[CLevelIssue, ...]:
        raise NotImplementedError
