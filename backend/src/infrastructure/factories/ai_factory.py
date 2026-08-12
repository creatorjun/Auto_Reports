# backend/src/infrastructure/factories/ai_factory.py
from src.application.ports.ai_port import AiPort
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.gemini_client import GeminiClient


class AiFactory:
    @staticmethod
    def create(settings: Settings) -> AiPort | None:
        if not settings.ai_enabled:
            return None
        return GeminiClient(settings.gemini_api_key)
