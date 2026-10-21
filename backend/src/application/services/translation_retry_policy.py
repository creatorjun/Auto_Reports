# backend/src/application/services/translation_retry_policy.py
from dataclasses import dataclass

from src.application.ports.security_news_translation_port import TranslationFailure


ATTEMPT_RESERVATION_SECONDS = 300
DAILY_LIMIT_MESSAGE = "오늘의 번역 요청 한도에 도달했습니다. 저장된 번역과 원문을 표시하며 다음 UTC 날짜에 재개합니다."
EXHAUSTED_MESSAGE = "일부 항목은 번역 자동 재시도가 제한되어 원문을 표시합니다."
FAILURE_MESSAGES = {
    "quota": "Gemini API 요청 한도에 도달하여 번역을 일시 중지했습니다. 저장된 번역과 원문을 표시합니다.",
    "billing": "Gemini API 크레딧이 부족하여 번역을 일시 중지했습니다. 저장된 번역과 원문을 표시합니다.",
    "authorization": "Gemini API 설정·인증 또는 모델 접근 권한을 확인해야 합니다. 저장된 번역과 원문을 표시합니다.",
    "provider": "번역 서비스 응답이 지연되어 일부 항목의 번역을 나중에 다시 시도합니다.",
    "invalid": "일부 번역 결과를 검증하지 못해 원문을 표시합니다. 잠시 후 다시 시도합니다.",
}


@dataclass(frozen=True)
class TranslationRetryDecision:
    message: str | None
    quota_failures: int | None = None
    request_delay_seconds: int | None = None
    extend_request_delay: bool = False
    restore_attempts: bool = False

    def item_delay_seconds(self, attempt_count: int) -> int:
        if self.restore_attempts:
            return self.request_delay_seconds or 0
        return min(86400, 300 * (2 ** min(attempt_count - 1, 8)))


def translation_retry_decision(
    failure: TranslationFailure | None, quota_failures: int,
) -> TranslationRetryDecision:
    if failure is None:
        return TranslationRetryDecision(message=None, quota_failures=0)
    if failure in {"quota", "billing", "authorization"}:
        count = quota_failures + 1
        delay = min(86400, 3600 * (2 ** min(count - 1, 5))) if failure == "quota" else 86400
        return TranslationRetryDecision(
            FAILURE_MESSAGES[failure], count, delay, restore_attempts=True,
        )
    return TranslationRetryDecision(
        FAILURE_MESSAGES[failure],
        request_delay_seconds=300 if failure == "provider" else None,
        extend_request_delay=True,
    )
