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
            logger.info("AI \ubd84\uc11d \ube44\ud65c\uc131\ud654 (AI_ENABLED=false)")
            return None

        w = report.widgets
        w14 = w.get(WidgetId.CREATED_VS_RESOLVED)
        w12 = w.get(WidgetId.SLA_MET_VS_VIOLATED)
        w11 = w.get(WidgetId.RESOLUTION_REPORT)
        w7  = w.get(WidgetId.SLA_DELAY_REASON)
        w1  = w.get(WidgetId.OVERDUE_ISSUES)

        def total(wid: WidgetId) -> int:
            widget = w.get(wid)
            return widget.total if widget is not None else 0

        # SLA \ucd08\uacfc \uc774\uc288 \uc0c1\uc138 \ubaa9\ub85d (\ucd5c\ub300 10\uac74)
        overdue_details = []
        if w1 and isinstance(w1.breakdown, dict):
            raw = w1.breakdown.get("issue_details", [])
            for d in raw[:10]:
                overdue_details.append(
                    f"  - {d.get('key','')} [{d.get('type','')}] "
                    f"{d.get('summary','')[:30]} / "
                    f"\uc0dd\uc131: {d.get('created','')} / "
                    f"\uc0c1\ud0dc: {d.get('resp_status','')} / "
                    f"\ucd08\uacfc: +{d.get('over_h',0)}h"
                )

        context = {
            "week_start":          report.week_start,
            "week_end":            report.week_end,
            "created":             w14.breakdown.get("\uc0dd\uc131", 0) if w14 else 0,
            "resolved":            w14.breakdown.get("\ud574\uacb0", 0) if w14 else 0,
            "sla_overdue":         total(WidgetId.OVERDUE_ISSUES),
            "issue_review":        total(WidgetId.ISSUE_REVIEW),
            "data_request":        total(WidgetId.DATA_REQUEST),
            "result_pending":      total(WidgetId.RESULT_PENDING),
            "lab_unassigned":      total(WidgetId.LAB_UNASSIGNED),
            "sla_met":             w12.breakdown.get("SLA \ub9cc\uc871", 0) if w12 else 0,
            "sla_violated":        w12.breakdown.get("SLA \uc704\ubc18", 0) if w12 else 0,
            "avg_resolution_days": w11.breakdown.get("avg_resolution_days", 0) if w11 else 0,
            "yearly_created":      total(WidgetId.YEARLY_CREATED),
            "yearly_resolved":     total(WidgetId.YEARLY_RESOLVED),
            "delay_reasons":       str(w7.breakdown) if w7 else "{}",
            "overdue_issue_list":  "\n".join(overdue_details) if overdue_details else "  (\ub370\uc774\ud130 \uc5c6\uc74c)",
        }
        logger.info("Gemini AI \ubd84\uc11d \uc694\uccad \uc911...")
        return self._ai.analyze(context)
