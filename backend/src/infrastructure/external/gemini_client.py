# backend/src/infrastructure/external/gemini_client.py
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from src.domain.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
\ub2f9\uc2e0\uc740 IT \uc11c\ube44\uc2a4 \uc6b4\uc601 \ubd84\uc11d \uc804\ubb38\uac00\uc785\ub2c8\ub2e4.
\uc544\ub798 TAC(\uae30\uc220\uc9c0\uc6d0\uc13c\ud130) \uc8fc\uac04 \uc6b4\uc601 \ub370\uc774\ud130\ub97c \ubd84\uc11d\ud558\uace0 JSON\uc73c\ub85c \uc751\ub2f5\ud558\uc138\uc694.

[\uc8fc\uac04 \uc6b4\uc601 \ub370\uc774\ud130]
- \ub370\uc774\ud130 \ubc94\uc704: {week_start} ~ {week_end}
- \uc774\ubc88 \uc8fc \uc0dd\uc131 \uc774\uc288: {created}\uac74
- \uc774\ubc88 \uc8fc \ud574\uacb0 \uc774\uc288: {resolved}\uac74
- SLA \ucd08\uacfc \ubbf8\ud574\uacb0 (30\uc77c \uc774\uc0c1): {sla_overdue}\uac74
- \uc774\uc288 \ub9ac\ubdf0 \uc911 \uc9c0\uc5f0: {issue_review}\uac74
- \uc790\ub8cc \uc694\uccad \uc911 \uc9c0\uc5f0: {data_request}\uac74
- \uacb0\uacfc \ub300\uae30 \uc911 \uc9c0\uc5f0: {result_pending}\uac74
- \uc5f0\uad6c\uc18c \ub300\uae30(\ub2f4\ub2f9\uc790 \ubbf8\uc9c0\uc815): {lab_unassigned}\uac74
- SLA \ub9cc\uc871: {sla_met}\uac74 / SLA \uc704\ubc18: {sla_violated}\uac74
- \ud3c9\uade0 \ud574\uacb0\uc2dc\uac04: {avg_resolution_days}\uc77c
- 2026\ub144 \ub204\uc801 \uc0dd\uc131: {yearly_created}\uac74 / \ub204\uc801 \ud574\uacb0: {yearly_resolved}\uac74
- SLA \uc9c0\uc5f0 \uc0ac\uc720: {delay_reasons}

[SLA \ucd08\uacfc \uc774\uc288 \uc0c1\uc138 (\ucd08\uacfc\uc2dc\uac04 \ub0b4\ub9bc\ucc28\uc21c, \ucd5c\ub300 10\uac74)]
{overdue_issue_list}

[\uc751\ub2f5 \ud615\uc2dd - \ubc18\ub4dc\uc2dc \uc544\ub798 JSON\ub9cc \ubc18\ud658]
{{
  "summary": "\ud575\uc2ec \uc6b4\uc601 \ud604\ud669 \uc694\uc57d (2~3\ubb38\uc7a5, \ud55c\uad6d\uc5b4). SLA \ucd08\uacfc \uc774\uc288 \uc911 \uc624\ub798\ub41c \ud2b9\uc774\uc0ac\ud56d \uc5b8\uae09",
  "risks": ["\ub9ac\uc2a4\ud06c1 (\uac00\ub2a5\ud558\uba74 \ud2b9\uc815 \ud0a4 \uba85\uc2dc)", "\ub9ac\uc2a4\ud06c2"],
  "recommendations": ["\uad8c\uace0\uc0ac\ud56d1", "\uad8c\uace0\uc0ac\ud56d2"],
  "sentiment": "good \ub610\ub294 warning \ub610\ub294 critical \uc911 \ud558\ub098"
}}

sentiment \ud310\ub2e8 \uae30\uc900:
- good: SLA \uc704\ubc18\uc728 20% \ubbf8\ub9cc, \ubbf8\ud574\uacb0 \uac10\uc18c \ucd94\uc138
- warning: SLA \uc704\ubc18\uc728 20~50%, \ub610\ub294 \ubbf8\ud574\uacb0 \uc99d\uac00
- critical: SLA \uc704\ubc18\uc728 50% \uc774\uc0c1, \ub610\ub294 SLA \ucd08\uacfc 30\uac74 \uc774\uc0c1
"""


class GeminiClient(AiPort):
    def __init__(self, api_key: str):
        if api_key:
            self._client = genai.Client(api_key=api_key)
        else:
            self._client = None

    def analyze(self, report_context: dict) -> Optional[AiAnalysis]:
        if not self._client:
            logger.warning("Gemini \ud074\ub77c\uc774\uc5b8\ud2b8 \ubbf8\ucd08\uae30\ud654 (API \ud0a4 \uc5c6\uc74c)")
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
            logger.error(f"Gemini \ubd84\uc11d \uc2e4\ud328: {e}")
            return None
