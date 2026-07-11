# backend/src/application/use_cases/generate_report.py
import dataclasses
import logging
from datetime import datetime, timedelta

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.report_assembler import ReportAssembler
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
    ):
        self._assembler = assembler
        self._analyzer = analyzer
        self._repository = repository
        self._cache = cache
        self._retention_weeks = retention_weeks

    async def execute(
        self,
        now: datetime | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Report:
        now = now or datetime.now(tz=KST)
        logger.info(f"보고서 생성 시작: {now}")

        new_report = await self._assembler.collect(
            now=end_date or now,
            week_start_override=start_date,
        )

        analysis = None
        try:
            analysis = await self._analyzer.analyze(new_report)
        except Exception as e:
            logger.error(f"AI 분석 실패 (원시 데이터는 저장됨): {e}")

        report_with_analysis = dataclasses.replace(new_report, ai_analysis=analysis)
        saved = await self._repository.save(report_with_analysis)

        await self._cache.set(saved.id, saved)
        await self._cache.set_latest_id(saved.id)
        logger.info(f"보고서 저장 완료 및 캐시 갱신: ID={saved.id}")

        await self._purge_expired(now)

        return saved

    async def _purge_expired(self, now: datetime) -> None:
        if self._retention_weeks == _RETENTION_DISABLED:
            return

        cutoff = (now - timedelta(weeks=self._retention_weeks)).date()
        logger.info(f"[도탄 정리] week_start < {cutoff} 인 보고서 삭제 시작 (retention={self._retention_weeks}주)")

        try:
            deleted_ids = await self._repository.delete_before(cutoff)
        except Exception as exc:
            logger.error(f"[도탄 정리] DB 삭제 실패: {exc}")
            return

        if not deleted_ids:
            logger.info("[도탄 정리] 삭제 대상 없음")
            return

        for rid in deleted_ids:
            try:
                await self._cache.delete(rid)
            except Exception:
                pass

        latest_id = await self._cache.get_latest_id()
        if latest_id in deleted_ids:
            await self._cache.set_latest_id(None)

        logger.info(f"[도탄 정리] {len(deleted_ids)}건 삭제 완료: {deleted_ids}")
