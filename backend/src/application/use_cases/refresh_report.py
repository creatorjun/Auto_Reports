# backend/src/application/use_cases/refresh_report.py
import logging
from datetime import datetime

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.report_assembler import ReportAssembler
from src.domain.repositories.report_repository import ReportRepository
from src.shared.constants import KST

logger = logging.getLogger(__name__)


class RefreshReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        repository: ReportRepository,
        cache: ReportCachePort,
    ):
        self._assembler = assembler
        self._repository = repository
        self._cache = cache

    async def execute(self) -> None:
        latest = await self._repository.find_latest()
        if latest is None:
            logger.info("[RefreshReport] 저장된 보고서 없음 — 갱신 생략")
            return

        now = datetime.now(tz=KST)
        week_start = datetime(
            latest.week_start.year,
            latest.week_start.month,
            latest.week_start.day,
            tzinfo=KST,
        )
        week_end = datetime(
            latest.week_end.year,
            latest.week_end.month,
            latest.week_end.day,
            tzinfo=KST,
        )

        new_report = await self._assembler.collect(
            now=week_end,
            week_start_override=week_start,
        )

        updated = await self._repository.update_widgets(latest.id, new_report)
        await self._cache.set(updated.id, updated)
        await self._cache.set_latest_id(updated.id)
        logger.info(f"[RefreshReport] 보고서 ID={updated.id} 갱신 완료 ({now.strftime('%H:%M:%S')})")
