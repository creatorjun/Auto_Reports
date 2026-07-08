# backend/src/infrastructure/external/gemini_client.py
import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from src.domain.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis

logger = logging.getLogger(__name__)


class GeminiClient(AiPort):
    def __init__(self, api_key: str):
        if api_key:
            self._client = genai.Client(api_key=api_key)
        else:
            self._client = None

    async def analyze(self, prompt: str) -> Optional[AiAnalysis]:
        if not self._client:
            logger.warning("Gemini 클라이언트 미초기화 (API 키 없음)")
            return None
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            return AiAnalysis(
                summary=data.get("summary", ""),
                risks=data.get("risks", []),
                recommendations=data.get("recommendations", []),
                sentiment=data.get("sentiment", "warning"),
            )
        except Exception as e:
            logger.error(f"Gemini 분석 실패: {e}")
            return None
