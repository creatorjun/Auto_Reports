# backend/src/application/use_cases/redeployment_report.py
from collections.abc import Callable
from datetime import datetime

from src.application.ports.redeployment_port import RedeploymentRepository, RedeploymentSourcePort
from src.domain.constants import KST
from src.domain.entities.redeployment_report import REDEPLOYMENT_START, RedeploymentReport, redeployment_refresh_due


class RedeploymentGenerationInProgress(Exception):
    pass


class RedeploymentReportUseCase:
    def __init__(self, source: RedeploymentSourcePort, repository: RedeploymentRepository,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._source = source
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(KST))

    async def get_latest(self) -> RedeploymentReport | None:
        return await self._repository.get_latest()

    async def generate(self, generated_by: str, force: bool = False) -> RedeploymentReport:
        if not await self._repository.try_generation_lock():
            raise RedeploymentGenerationInProgress
        now = self._clock()
        previous = await self._repository.get_latest()
        if not force and previous and previous.generated_at >= redeployment_refresh_due(now):
            return previous
        jql, tickets, warnings = await self._source.fetch(now)
        return await self._repository.save(RedeploymentReport(
            id=0, period_start=REDEPLOYMENT_START, generated_at=now,
            generated_by=generated_by, source_jql=jql, tickets=tickets, warnings=warnings,
        ))
