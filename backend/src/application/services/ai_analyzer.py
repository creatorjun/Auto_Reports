# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)


class AiAnalyzer:
    def __init__(self, ai: AiPort, enabled: bool = True):
        self._ai = ai
        self._enabled = enabled

    def analyze(self, report: Report) -> Optional[AiAnalysis]:
        if not self._enabled:
            logger.info("AI 분석 비활성화 (AI_ENABLED=false)")
            return None

        w = report.widgets
        w14 = w.get(WidgetId.CREATED_VS_RESOLVED)
        w12 = w.get(WidgetId.SLA_MET_VS_VIOLATED)
        w11 = w.get(WidgetId.RESOLUTION_REPORT)
        w7  = w.get(WidgetId.SLA_DELAY_REASON)

        def total(wid: WidgetId) -> int:
            widget = w.get(wid)
            return widget.total if widget is not None else 0

        context = {
            "week_start":          report.week_start,
            "week_end":            report.week_end,
            "created":             w14.breakdown.get("생성", 0) if w14 else 0,
            "resolved":            w14.breakdown.get("해결", 0) if w14 else 0,
            "sla_overdue":         total(WidgetId.OVERDUE_ISSUES),
            "dev_delay":           total(WidgetId.DEV_SLA_DELAY),
            "tac_delay":           total(WidgetId.TAC_QA_SLA_DELAY),
            "lab_unassigned":      total(WidgetId.LAB_UNASSIGNED),
            "sla_met":             w12.breakdown.get("SLA 만족", 0) if w12 else 0,
            "sla_violated":        w12.breakdown.get("SLA 위반", 0) if w12 else 0,
            "avg_resolution_days": w11.breakdown.get("avg_resolution_days", 0) if w11 else 0,
            "yearly_created":      total(WidgetId.YEARLY_CREATED),
            "yearly_resolved":     total(WidgetId.YEARLY_RESOLVED),
            "delay_reasons":       str(w7.breakdown) if w7 else "{}",
        }
        logger.info("Gemini AI 분석 요청 중...")
        return self._ai.analyze(context)
