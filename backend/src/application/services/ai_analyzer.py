# backend/src/application/services/ai_analyzer.py
import logging
from typing import Optional

from src.domain.entities.report import NewReport
from src.application.ports.ai_port import AiPort
from src.application.ports.report_analyzer_port import ReportAnalyzerPort
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.domain.value_objects.widget_id import WidgetId
from src.domain.constants import AI_OVERDUE_DETAIL_LIMIT

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
- SLA 만족: {sla_met}건 / SLA 위반: {sla_violated}건
- 평균 해결시간: {avg_resolution_days}일
- 올해 누적 생성: {yearly_created}건 / 누적 해결: {yearly_resolved}건
- SLA 지연 사유: {delay_reasons}

[SLA 초과 이슈 상세 (초과시간 내림차순, 최대 {overdue_limit}건)]
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

_DEFAULTS: dict = {
    "created": 0,
    "resolved": 0,
    "sla_violated": 0,
    "avg_resolution_days": 0,
    "delay_reasons": "{}",
    "overdue_issue_list": "  (데이터 없음)",
}


class AiAnalyzer(ReportAnalyzerPort):
    def __init__(self, ai: AiPort | None, enabled: bool = True):
        self._ai = ai
        self._enabled = enabled

    async def analyze(self, report: NewReport) -> Optional[AiAnalysis]:
        if not self._enabled or self._ai is None:
            logger.info("AI 분석 비활성화 (AI_ENABLED=false 또는 ai=None)")
            return None

        widgets = report.widgets

        def total(widget_id: WidgetId) -> int:
            widget = widgets.get(widget_id)
            return widget.total if widget is not None else 0

        ai_ctx: dict = dict(_DEFAULTS)
        for widget_id in (
            WidgetId.OVERDUE_ISSUES,
            WidgetId.CREATED_VS_RESOLVED,
            WidgetId.SLA_MET_VS_VIOLATED,
            WidgetId.RESOLUTION_REPORT,
            WidgetId.SLA_DELAY_REASON,
        ):
            widget = widgets.get(widget_id)
            if widget is not None:
                ai_ctx.update(widget.ai_context())

        context = {
            **ai_ctx,
            "week_start": report.week_start,
            "week_end": report.week_end,
            "sla_overdue": total(WidgetId.OVERDUE_ISSUES),
            "issue_review": total(WidgetId.ISSUE_REVIEW),
            "data_request": total(WidgetId.DATA_REQUEST),
            "result_pending": total(WidgetId.RESULT_PENDING),
            "sla_met": 0,
            "yearly_created": total(WidgetId.YEARLY_CREATED),
            "yearly_resolved": total(WidgetId.YEARLY_RESOLVED),
            "overdue_limit": AI_OVERDUE_DETAIL_LIMIT,
        }

        prompt = PROMPT_TEMPLATE.format(**context)
        logger.info("Gemini AI 분석 요청 중...")
        return await self._ai.analyze(prompt)
