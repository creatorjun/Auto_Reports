# backend/src/infrastructure/external/gemini_client.py
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from src.domain.value_objects.ai_analysis import AiAnalysis

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
당신은 IT 서비스 운영 분석 전문가입니다.
아래 TAC(기술지원센터) 주간 운영 데이터를 분석하고 JSON으로 응답하세요.

[주간 운영 데이터]
- 데이터 범위: {week_start} ~ {week_end}
- 이번 주 생성 이슈: {created}건
- 이번 주 해결 이슈: {resolved}건
- SLA 초과 미해결 (30일 이상): {sla_overdue}건
- 개발 SLA 지연: {dev_delay}건
- TAC & QA SLA 지연: {tac_delay}건
- 연구소 대기(담당자 미지정): {lab_unassigned}건
- SLA 만족: {sla_met}건 / SLA 위반: {sla_violated}건
- 평균 해결시간: {avg_resolution_days}일
- 2026년 누적 생성: {yearly_created}건 / 누적 해결: {yearly_resolved}건
- SLA 지연 사유: {delay_reasons}

[응답 형식 - 반드시 아래 JSON만 반환]
{{
  "summary": "핵심 운영 현황 요약 (2~3문장, 한국어)",
  "risks": ["리스크1", "리스크2"],
  "recommendations": ["권고사항1", "권고사항2"],
  "sentiment": "good 또는 warning 또는 critical 중 하나"
}}

sentiment 판단 기준:
- good: SLA 위반율 20% 미만, 미해결 감소 추세
- warning: SLA 위반율 20~50%, 또는 미해결 증가
- critical: SLA 위반율 50% 이상, 또는 SLA 초과 30건 이상
"""


class GeminiClient:
    def __init__(self, api_key: str):
        if api_key:
            self._client = genai.Client(api_key=api_key)
        else:
            self._client = None

    def analyze(self, report_context: dict) -> Optional[AiAnalysis]:
        if not self._client:
            logger.warning("Gemini 클라이언트 미초기화 (API 키 없음)")
            return None
        prompt = PROMPT_TEMPLATE.format(**report_context)
        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            return AiAnalysis(
                summary=data.get("summary", ""),
                risks=data.get("risks", []),
                recommendations=data.get("recommendations", []),
                sentiment=data.get("sentiment", "warning")
            )
        except Exception as e:
            logger.error(f"Gemini 분석 실패: {e}")
            return None
