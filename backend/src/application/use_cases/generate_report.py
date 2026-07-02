# backend/src/application/use_cases/generate_report.py
import dataclasses
import logging
from datetime import datetime

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.report_collector import ReportCollector
from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository

logger = logging.getLogger(__name__)


class GenerateReportUseCase:
    def __init__(
        self,
        collector: ReportCollector,
        analyzer: AiAnalyzer,
        repository: ReportRepository
    ):
        self._collector = collector
        self._analyzer = analyzer
        self._repository = repository

    async def execute(self, now: datetime | None = None) -> Report:
        now = now or datetime.now()
        logger.info(f"보고서 생성 시작: {now}")

        report = self._collector.collect(now)
        analysis = self._analyzer.analyze(report)
        report_with_analysis = dataclasses.replace(report, ai_analysis=analysis)
        saved = await self._repository.save(report_with_analysis)

        logger.info(f"보고서 저장 완료: ID={saved.id}")
        return saved
