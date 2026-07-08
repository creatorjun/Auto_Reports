# backend/src/application/use_cases/generate_report.py
import dataclasses
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.report_assembler import ReportAssembler
from src.domain.entities.report import Report
from src.domain.repositories.report_repository import ReportRepository

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class GenerateReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        analyzer: AiAnalyzer,
        repository: ReportRepository,
    ):
        self._assembler = assembler
        self._analyzer = analyzer
        self._repository = repository

    async def execute(self, now: datetime | None = None) -> Report:
        now = now or datetime.now(tz=KST)
        logger.info(f"보고서 생성 시작: {now}")

        report = await self._assembler.collect(now)

        analysis = None
        try:
            analysis = self._analyzer.analyze(report)
        except Exception as e:
            logger.error(f"AI 분석 실패 (원시 데이터는 저장됨): {e}")

        report_with_analysis = dataclasses.replace(report, ai_analysis=analysis)
        saved = await self._repository.save(report_with_analysis)

        logger.info(f"보고서 저장 완료: ID={saved.id}")
        return saved
