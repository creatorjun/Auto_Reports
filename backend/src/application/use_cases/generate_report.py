# backend/src/application/use_cases/generate_report.py
import dataclasses
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase, extract_todo_issues
from src.domain.entities.report import Report
from src.domain.ports.report_analyzer_port import ReportAnalyzerPort
from src.domain.repositories.report_repository import ReportRepository
from src.shared.constants import KST

logger = logging.getLogger(__name__)

_RETENTION_DISABLED = 0


class GenerateReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        analyzer: ReportAnalyzerPort,
        repository: ReportRepository,
        cache: ReportCachePort,
        retention_weeks: int = 52,
        notify: Optional[NotifyTodoIssuesUseCase] = None,
    ):
        self._assembler = assembler
        self._analyzer = analyzer
        self._repository = repository
        self._cache = cache
        self._retention_weeks = retention_weeks
        self._notify = notify

    async def execute(
        self,
        now: datetime | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Report:
        now = now or datetime.now(tz=KST)
        logger.info(f"\ubcf4\uace0\uc11c \uc0dd\uc131 \uc2dc\uc791: {now}")

        new_report = await self._assembler.collect(
            now=end_date or now,
            week_start_override=start_date,
        )

        analysis = None
        try:
            analysis = await self._analyzer.analyze(new_report)
        except Exception as e:
            logger.error(f"AI \ubd84\uc11d \uc2e4\ud328 (\uc6d0\uc2dc \ub370\uc774\ud130\ub294 \uc800\uc7a5\ub428): {e}")

        report_with_analysis = dataclasses.replace(new_report, ai_analysis=analysis)
        saved = await self._repository.save(report_with_analysis)

        await self._cache.set(saved.id, saved)
        await self._cache.set_latest_id(saved.id)
        logger.info(f"\ubcf4\uace0\uc11c \uc800\uc7a5 \uc644\ub8cc \ubc0f \uce90\uc2dc \uac31\uc2e0: ID={saved.id}")

        await self._purge_expired(now)

        if self._notify is not None:
            todo_issues = extract_todo_issues(new_report.widgets)
            if todo_issues:
                try:
                    await self._notify.execute(todo_issues)
                except Exception as exc:
                    logger.error(f"[GenerateReport] \uba54\uc77c \ubc1c\uc1a1 \uc2e4\ud328: {exc}")

        return saved

    async def _purge_expired(self, now: datetime) -> None:
        if self._retention_weeks == _RETENTION_DISABLED:
            return

        cutoff = (now - timedelta(weeks=self._retention_weeks)).date()
        logger.info(f"[\ub3c4\ud0dc \uc815\ub9ac] week_start < {cutoff} \uc778 \ubcf4\uace0\uc11c \uc0ad\uc81c \uc2dc\uc791 (retention={self._retention_weeks}\uc8fc)")

        try:
            deleted_ids = await self._repository.delete_before(cutoff)
        except Exception as exc:
            logger.error(f"[\ub3c4\ud0dc \uc815\ub9ac] DB \uc0ad\uc81c \uc2e4\ud328: {exc}")
            return

        if not deleted_ids:
            logger.info("[\ub3c4\ud0dc \uc815\ub9ac] \uc0ad\uc81c \ub300\uc0c1 \uc5c6\uc74c")
            return

        for rid in deleted_ids:
            try:
                await self._cache.delete(rid)
            except Exception:
                pass

        latest_id = await self._cache.get_latest_id()
        if latest_id in deleted_ids:
            await self._cache.set_latest_id(None)

        logger.info(f"[\ub3c4\ud0dc \uc815\ub9ac] {len(deleted_ids)}\uac74 \uc0ad\uc81c \uc644\ub8cc: {deleted_ids}")
