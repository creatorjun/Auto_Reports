# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.infrastructure.external.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class AiAnalyzer:
    def __init__(self, gemini: GeminiClient):
        self._gemini = gemini

    def analyze(self, report: Report) -> Optional[AiAnalysis]:
        w = report.widgets
        w14 = w.get("w14")
        w12 = w.get("w12")
        w11 = w.get("w11")
        w7 = w.get("w7")

        context = {
            "week_start": report.week_start,
            "week_end": report.week_end,
            "created": w14.breakdown.get("생성", 0) if w14 else 0,
            "resolved": w14.breakdown.get("해결", 0) if w14 else 0,
            "sla_overdue": w.get("w1", type("W", (), {"total": 0})()).total,
            "dev_delay": w.get("w2", type("W", (), {"total": 0})()).total,
            "tac_delay": w.get("w3", type("W", (), {"total": 0})()).total,
            "lab_unassigned": w.get("w4", type("W", (), {"total": 0})()).total,
            "sla_met": w12.breakdown.get("SLA 만족", 0) if w12 else 0,
            "sla_violated": w12.breakdown.get("SLA 위반", 0) if w12 else 0,
            "avg_resolution_days": w11.breakdown.get("avg_resolution_days", 0) if w11 else 0,
            "yearly_created": w.get("w8", type("W", (), {"total": 0})()).total,
            "yearly_resolved": w.get("w9", type("W", (), {"total": 0})()).total,
            "delay_reasons": str(w7.breakdown) if w7 else "{}",
        }
        logger.info("Gemini AI 분석 요청 중...")
        return self._gemini.analyze(context)
