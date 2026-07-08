# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.entities.widget_data import CreatedVsResolvedWidgetData, OverdueWidgetData, RecentIssueWidgetData, SlaDelayWidgetData, SlaMetVsViolatedWidgetData
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

        widgets = report.widgets
        created_vs_resolved = widgets.get(WidgetId.CREATED_VS_RESOLVED)
        sla_met_vs_violated = widgets.get(WidgetId.SLA_MET_VS_VIOLATED)
        recent_issues = widgets.get(WidgetId.RESOLUTION_REPORT)
        delay_reasons = widgets.get(WidgetId.SLA_DELAY_REASON)
        overdue_issues = widgets.get(WidgetId.OVERDUE_ISSUES)

        def total(widget_id: WidgetId) -> int:
            widget = widgets.get(widget_id)
            return widget.total if widget is not None else 0

        overdue_data = overdue_issues.data if overdue_issues and isinstance(overdue_issues.data, OverdueWidgetData) else None
        overdue_details = []
        if overdue_data is not None:
            for detail in overdue_data.issue_details[:10]:
                overdue_details.append(
                    f"  - {detail.key} [{detail.type}] "
                    f"{detail.summary[:30]} / "
                    f"생성: {detail.created} / "
                    f"상태: {detail.resp_status} / "
                    f"초과: +{detail.over_h}h"
                )

        created_resolved_data = (
            created_vs_resolved.data
            if created_vs_resolved and isinstance(created_vs_resolved.data, CreatedVsResolvedWidgetData)
            else None
        )
        sla_data = (
            sla_met_vs_violated.data
            if sla_met_vs_violated and isinstance(sla_met_vs_violated.data, SlaMetVsViolatedWidgetData)
            else None
        )
        recent_data = (
            recent_issues.data
            if recent_issues and isinstance(recent_issues.data, RecentIssueWidgetData)
            else None
        )
        delay_reason_data = (
            delay_reasons.data
            if delay_reasons and isinstance(delay_reasons.data, SlaDelayWidgetData)
            else None
        )

        avg_resolution_days = 0
        if recent_data is not None and recent_data.issue_details:
            avg_resolution_days = round(
                sum(detail.elapsed_days for detail in recent_data.issue_details) / len(recent_data.issue_details),
                1,
            )

        context = {
            "week_start": report.week_start,
            "week_end": report.week_end,
            "created": created_resolved_data.created if created_resolved_data is not None else 0,
            "resolved": created_resolved_data.resolved if created_resolved_data is not None else 0,
            "sla_overdue": total(WidgetId.OVERDUE_ISSUES),
            "issue_review": total(WidgetId.ISSUE_REVIEW),
            "data_request": total(WidgetId.DATA_REQUEST),
            "result_pending": total(WidgetId.RESULT_PENDING),
            "lab_unassigned": total(WidgetId.LAB_UNASSIGNED),
            "sla_met": 0,
            "sla_violated": (
                sla_data.initial_response_violations + sla_data.resolution_violations
                if sla_data is not None
                else 0
            ),
            "avg_resolution_days": avg_resolution_days,
            "yearly_created": total(WidgetId.YEARLY_CREATED),
            "yearly_resolved": total(WidgetId.YEARLY_RESOLVED),
            "delay_reasons": str(delay_reason_data.by_status) if delay_reason_data is not None else "{}",
            "overdue_issue_list": "\n".join(overdue_details) if overdue_details else "  (데이터 없음)",
        }
        logger.info("Gemini AI 분석 요청 중...")
        return self._ai.analyze(context)
