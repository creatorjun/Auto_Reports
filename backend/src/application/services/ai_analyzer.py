# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis

logger = logging.getLogger(__name__)


class AiAnalyzer:
    def __init__(self, ai: AiPort, enabled: bool = True):
        self._ai = ai
        self._enabled = enabled

    def analyze(self, report: Report) -> Optional[AiAnalysis]:
        if not self._enabled:
            logger.info("유AI 분석 비활성화 (AI_ENABLED=false)")
            return None

        w = report.widgets
        w14 = w.get("w14")
        w12 = w.get("w12")
        w11 = w.get("w11")
        w7  = w.get("w7")

        def total(key): return w.get(key, type("W", (), {"total": 0})()).total

        context = {
            "week_start":          report.week_start,
            "week_end":            report.week_end,
            "created":             w14.breakdown.get("생성", 0) if w14 else 0,
            "resolved":            w14.breakdown.get("해결", 0) if w14 else 0,
            "sla_overdue":         total("w1"),
            "dev_delay":           total("w2"),
            "tac_delay":           total("w3"),
            "lab_unassigned":      total("w4"),
            "sla_met":             w12.breakdown.get("SLA 만족", 0) if w12 else 0,
            "sla_violated":        w12.breakdown.get("SLA 위반", 0) if w12 else 0,
            "avg_resolution_days": w11.breakdown.get("avg_resolution_days", 0) if w11 else 0,
            "yearly_created":      total("w8"),
            "yearly_resolved":     total("w9"),
            "delay_reasons":       str(w7.breakdown) if w7 else "{}",
        }
        logger.info("Gemini AI 분석 요청 중...")
        return self._ai.analyze(context)
