# backend/tests/unit/application/test_ai_analyzer.py
"""
AiAnalyzer 프롬프트 생성 단위 테스트.

Gemini 호출 없이 프롬프트 포맷팅 로직만 검증한다.
"""
import datetime

import pytest

from src.application.services.ai_analyzer import AiAnalyzer
from src.domain.entities.report import NewReport
from src.domain.value_objects.ai_analysis import AiAnalysis


class TestAiAnalyzerDisabled:
    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self, mock_ai_port):
        analyzer = AiAnalyzer(ai=mock_ai_port, enabled=False)
        report = NewReport(
            week_start=datetime.date(2026, 7, 1),
            week_end=datetime.date(2026, 7, 7),
            report_date="2026-07-07 23:00",
        )
        result = await analyzer.analyze(report)
        assert result is None
        mock_ai_port.analyze.assert_not_awaited()


class TestAiAnalyzerEnabled:
    @pytest.mark.asyncio
    async def test_calls_ai_port_with_prompt(self, mock_ai_port, sample_new_report):
        analyzer = AiAnalyzer(ai=mock_ai_port, enabled=True)
        result = await analyzer.analyze(sample_new_report)
        assert isinstance(result, AiAnalysis)
        mock_ai_port.analyze.assert_awaited_once()
        # 프롬프트에 주요 파라메터가 포함되어야 함
        prompt_arg: str = mock_ai_port.analyze.call_args[0][0]
        assert "TAC" in prompt_arg
        assert "JSON" in prompt_arg

    @pytest.mark.asyncio
    async def test_returns_none_when_ai_port_returns_none(self, sample_new_report):
        from unittest.mock import AsyncMock
        from src.domain.ports.ai_port import AiPort
        null_port = AsyncMock(spec=AiPort)
        null_port.analyze.return_value = None
        analyzer = AiAnalyzer(ai=null_port, enabled=True)
        result = await analyzer.analyze(sample_new_report)
        assert result is None
