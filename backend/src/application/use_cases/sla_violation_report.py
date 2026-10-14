# backend/src/application/use_cases/sla_violation_report.py
import asyncio
from collections.abc import Callable
from datetime import date, datetime

from src.application.errors import EntityNotFoundError
from src.application.ports.sla_violation_port import SlaViolationRepository, SlaViolationSourcePort
from src.application.services.sla_violation_metrics import build_sla_violation_report, sla_violation_window
from src.domain.constants import KST
from src.domain.entities.sla_violation_report import (
    SlaViolationPeriod,
    SlaViolationReport,
    SlaViolationReportSummary,
)


class SlaViolationGenerationInProgressError(Exception):
    pass


class SlaViolationSourceError(Exception):
    pass


class SlaViolationReportUseCase:
    def __init__(
        self,
        source: SlaViolationSourcePort,
        repository: SlaViolationRepository,
        generation_lock: asyncio.Lock,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._source = source
        self._repository = repository
        self._generation_lock = generation_lock
        self._clock = clock or (lambda: datetime.now(KST))

    async def generate(
        self,
        period: SlaViolationPeriod,
        selected_date: date,
        generated_by: str,
    ) -> SlaViolationReport:
        if selected_date > self._clock().astimezone(KST).date():
            raise ValueError("미래 날짜의 보고서는 생성할 수 없습니다.")
        start, end = sla_violation_window(period, selected_date)
        if self._generation_lock.locked():
            raise SlaViolationGenerationInProgressError
        async with self._generation_lock:
            try:
                issues = await self._source.fetch_issues(start, end)
            except RuntimeError as error:
                raise SlaViolationSourceError("Jira SLA 데이터를 불러오지 못했습니다.") from error
            report = build_sla_violation_report(
                issues=issues,
                period=period,
                selected_date=selected_date,
                generated_at=self._clock(),
                generated_by=generated_by,
            )
            return await self._repository.save(report)

    async def get_latest(self) -> SlaViolationReport | None:
        return await self._repository.get_latest()

    async def get_by_id(self, report_id: int) -> SlaViolationReport:
        report = await self._repository.get_by_id(report_id)
        if report is None:
            raise EntityNotFoundError("SLA violation report", report_id)
        return report

    async def list_summaries(self, limit: int = 20, offset: int = 0) -> list[SlaViolationReportSummary]:
        return await self._repository.list_summaries(limit, offset)
