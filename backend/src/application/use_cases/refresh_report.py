# backend/src/application/use_cases/refresh_report.py
import dataclasses
import logging
from datetime import datetime
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.notify_tac_assigned import NotifyTacAssignedUseCase
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase, extract_todo_issues
from src.application.ports.report_repository import ReportRepository
from src.domain.constants import KST
from src.domain.entities.report import NewReport, Report, ReportScope

logger = logging.getLogger(__name__)


class RefreshReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        repository: ReportRepository,
        cache: ReportCachePort,
        notify: Optional[NotifyTodoIssuesUseCase] = None,
        notify_tac: Optional[NotifyTacAssignedUseCase] = None,
    ):
        self._assembler = assembler
        self._repository = repository
        self._cache = cache
        self._notify = notify
        self._notify_tac = notify_tac

    async def execute(self) -> None:
        latest = await self._repository.find_latest()
        now = datetime.now(tz=KST)
        annual = await self._repository.find_annual(now.year)
        if latest is None and annual is None:
            logger.info("[RefreshReport] \uac31\uc2e0\ud560 \uc77c\ubc18/\uc5f0\uac04 \ubcf4\uace0\uc11c \uc5c6\uc74c \u2014 \uac31\uc2e0 \uc0dd\ub7b5")
            return

        refreshed_latest: NewReport | None = None
        if latest is not None:
            refreshed_latest = await self._refresh_one(latest, self._report_end(latest))
            await self._cache.set_latest_id(latest.id)

        if annual is not None:
            await self._refresh_one(annual, now)

        if refreshed_latest is None:
            return

        if self._notify is not None:
            todo_issues = extract_todo_issues(refreshed_latest.widgets)
            if todo_issues:
                try:
                    await self._notify.execute(todo_issues)
                except Exception as exc:
                    logger.error(f"[RefreshReport] \ud560\uc77c \uba54\uc77c \uc2e4\ud328: {exc}")

        if self._notify_tac is not None:
            try:
                await self._notify_tac.execute(refreshed_latest.widgets)
            except Exception as exc:
                logger.error(f"[RefreshReport] TAC \ub2f4\ub2f9\uc790 \uba54\uc77c \uc2e4\ud328: {exc}")

    async def _refresh_one(self, report: Report, end_at: datetime) -> NewReport:
        start_at = datetime(
            report.week_start.year,
            report.week_start.month,
            report.week_start.day,
            tzinfo=KST,
        )
        refreshed = await self._assembler.collect(
            now=end_at,
            week_start_override=start_at,
        )
        refreshed = dataclasses.replace(
            refreshed,
            scope=report.scope,
            report_year=report.report_year,
        )
        updated = await self._repository.update_widgets(report.id, refreshed)
        await self._cache.set(updated.id, updated)
        label = "\uc5f0\uac04" if report.scope == ReportScope.ANNUAL else "\uc77c\ubc18"
        logger.info(
            "[RefreshReport] %s \ubcf4\uace0\uc11c ID=%d \uac31\uc2e0 \uc644\ub8cc (%s)",
            label,
            updated.id,
            end_at.strftime("%H:%M:%S"),
        )
        return refreshed

    @staticmethod
    def _report_end(report: Report) -> datetime:
        return datetime(
            report.week_end.year,
            report.week_end.month,
            report.week_end.day,
            hour=23,
            minute=59,
            second=59,
            tzinfo=KST,
        )
