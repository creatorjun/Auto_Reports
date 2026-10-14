# backend/src/application/ports/sla_violation_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.sla_violation_report import (
    SlaViolationIssue,
    SlaViolationReport,
    SlaViolationReportSummary,
)


class SlaViolationSourcePort(ABC):
    @abstractmethod
    async def fetch_issues(self, start: datetime, end: datetime) -> tuple[SlaViolationIssue, ...]:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError


class SlaViolationRepository(ABC):
    @abstractmethod
    async def save(self, report: SlaViolationReport) -> SlaViolationReport:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self) -> SlaViolationReport | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, report_id: int) -> SlaViolationReport | None:
        raise NotImplementedError

    @abstractmethod
    async def list_summaries(self, limit: int, offset: int) -> list[SlaViolationReportSummary]:
        raise NotImplementedError
