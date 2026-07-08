# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import Report
from src.domain.entities.widget_data import (
    CreatedVsResolvedWidgetData,
    OverdueWidgetData,
    RecentIssueWidgetData,
    SlaDelayWidgetData,
    SlaMetVsViolatedWidgetData,
)
from src.domain.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
당신은 IT 서비스 운영 분석 전문가입니다.
아래 TAC(기술지원센터) 주간 운영 데이터를 분석하고 JSON으로 응답하세요.

[주간 운영 데이터]
- 데이터 범위: {week_start} ~ {week_end}
- 이번 주 생성 이슈: {created}건
- 이번 주 해결 이슈: {resolved}건
- SLA 초과 미해결 (30일 이상): {sla_overdue}건
- 이슈 리뷰 중 지연: {issue_review}건
- 자료 요청 중 지연: {data_request}건
- 결과 대기 중 지연: {result_pending}건
- 연구소 대기(담당자 미지정): {lab_unassigned}건
- SLA 만족: {sla_met}건 / SLA 위반: {sla_violated}건
- 평균 해결시간: {avg_resolution_days}일
- 2026년 누적 생성: {yearly_created}건 / 누적 해결: {yearly_resolved}건
- SLA 지연 사유: {delay_reasons}

[SLA 초과 이슈 상세 (초과시간 내림차순, 최대 10건)]
{overdue_issue_list}

[응답 형식 - 반드시 아래 JSON만 반환]
{{
  "summary": "핵심 운영 현황 요약 (2~3문장, 한국어). SLA 초과 이슈 중 오래된 특이사항 언급",
  "risks": ["리스크1 (가능하면 특정 키 명시)", "리스크2"],
  "recommendations": ["권고사항1", "권고사항2"],
  "sentiment": "good 또는 warning 또는 critical 중 하나"
}}

sentiment 판단 기준:
- good: SLA 위반율 20% 미만, 미해결 감소 추세
- warning: SLA 위반율 20~50%, 또는 미해결 증가
- critical: SLA 위반율 50% 이상, 또는 SLA 초과 30건 이상
"""


class AiAnalyzer:
    def __init__(self, ai: AiPort, enabled: bool = True):
        self._ai = ai
        self._enabled = enabled

    def analyze(self, report: Report) -> Optional[AiAnalysis]:
        if not self._enabled:
            logger.info("AI 분석 비활성화 (AI_ENABLED=false)")
            return None

        widgets = report.widgets

        def total(widget_id: WidgetId) -> int:
            widget = widgets.get(widget_id)
            return widget.total if widget is not None else 0

        overdue_issues = widgets.get(WidgetId.OVERDUE_ISSUES)
        overdue_data = (
            overdue_issues.data
            if overdue_issues and isinstance(overdue_issues.data, OverdueWidgetData)
            else None
        )
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

        created_vs_resolved = widgets.get(WidgetId.CREATED_VS_RESOLVED)
        created_resolved_data = (
            created_vs_resolved.data
            if created_vs_resolved and isinstance(created_vs_resolved.data, CreatedVsResolvedWidgetData)
            else None
        )

        sla_met_vs_violated = widgets.get(WidgetId.SLA_MET_VS_VIOLATED)
        sla_data = (
            sla_met_vs_violated.data
            if sla_met_vs_violated and isinstance(sla_met_vs_violated.data, SlaMetVsViolatedWidgetData)
            else None
        )

        recent_issues = widgets.get(WidgetId.RESOLUTION_REPORT)
        recent_data = (
            recent_issues.data
            if recent_issues and isinstance(recent_issues.data, RecentIssueWidgetData)
            else None
        )

        delay_reasons = widgets.get(WidgetId.SLA_DELAY_REASON)
        delay_reason_data = (
            delay_reasons.data
            if delay_reasons and isinstance(delay_reasons.data, SlaDelayWidgetData)
            else None
        )

        avg_resolution_days = 0
        if recent_data is not None and recent_data.issue_details:
            avg_resolution_days = round(
                sum(d.elapsed_days for d in recent_data.issue_details) / len(recent_data.issue_details),
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

        prompt = PROMPT_TEMPLATE.format(**context)
        logger.info("Gemini AI 분석 요청 중...")
        return self._ai.analyze(prompt)
