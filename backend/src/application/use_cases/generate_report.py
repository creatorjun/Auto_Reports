# backend/src/application/use_cases/generate_report.py
import dataclasses
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.report_assembler import ReportAssembler
from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository
from src.shared.cache import LruCache
from src.shared.constants import KST

logger = logging.getLogger(__name__)

_LATEST_KEY = "__latest__"


class GenerateReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        analyzer: AiAnalyzer,
        repository: ReportRepository,
        cache: LruCache,
    ):
        self._assembler = assembler
        self._analyzer = analyzer
        self._repository = repository
        self._cache = cache

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

        self._cache.set(saved.id, saved)
        self._cache.set(_LATEST_KEY, saved)
        logger.info(f"보고서 저장 완료 및 쳨시 갱신: ID={saved.id}")
        return saved
