# backend/tests/unit/application/test_generate_report_uc.py
"""
GenerateReportUseCase 단위 테스트.

JiraPort, AiPort, ReportRepository 모두 Mock으로 대체하므로
외부 I/O 없이 코리직력만 검증한다.
"""
import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.domain.entities.report import NewReport, Report
from src.domain.value_objects.ai_analysis import AiAnalysis


@pytest.fixture
def assembler_mock(sample_new_report: NewReport):
    m = AsyncMock()
    m.collect.return_value = sample_new_report
    return m


@pytest.fixture
def analyzer_mock(good_ai_analysis: AiAnalysis):
    m = AsyncMock(spec=AiAnalyzer)
    m.analyze.return_value = good_ai_analysis
    return m


class TestGenerateReportUseCase:
    @pytest.mark.asyncio
    async def test_execute_returns_saved_report(
        self, assembler_mock, analyzer_mock, mock_report_repository, sample_report
    ):
        uc = GenerateReportUseCase(assembler_mock, analyzer_mock, mock_report_repository)
        result = await uc.execute(now=datetime.datetime(2026, 7, 7, 23, 0))
        assert isinstance(result, Report)
        assert result.id == sample_report.id

    @pytest.mark.asyncio
    async def test_execute_calls_assembler_and_analyzer(
        self, assembler_mock, analyzer_mock, mock_report_repository
    ):
        uc = GenerateReportUseCase(assembler_mock, analyzer_mock, mock_report_repository)
        await uc.execute(now=datetime.datetime(2026, 7, 7, 23, 0))
        assembler_mock.collect.assert_awaited_once()
        analyzer_mock.analyze.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_saves_even_if_analyzer_raises(
        self, assembler_mock, mock_report_repository
    ):
        """AI 분석에 실패해도 보고서는 저장되어야 한다."""
        failing_analyzer = AsyncMock(spec=AiAnalyzer)
        failing_analyzer.analyze.side_effect = RuntimeError("이것은 폭�")
        uc = GenerateReportUseCase(assembler_mock, failing_analyzer, mock_report_repository)
        result = await uc.execute(now=datetime.datetime(2026, 7, 7, 23, 0))
        # ai_analysis 없이도 저장 호출되어야 함
        mock_report_repository.save.assert_awaited_once()
        assert isinstance(result, Report)
