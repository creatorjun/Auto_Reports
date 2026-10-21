# backend/src/infrastructure/factories/ai_factory.py
from src.application.ports.ai_port import AiPort
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.gemini_client import GeminiClient
from src.infrastructure.external.rovo_automation_client import RovoAutomationClient


class AiFactory:
    @staticmethod
    def create(settings: Settings) -> AiPort | None:
        if not settings.ai_enabled:
            return None
        if settings.ai_provider == "rovo_automation":
            return RovoAutomationClient(
                webhook_url=settings.rovo_automation_webhook_url,
                webhook_token=settings.rovo_automation_webhook_token,
                result_issue_key=settings.rovo_automation_result_issue_key,
                jira_base_url=settings.jira_base_url,
                jira_email=settings.jira_email,
                jira_api_token=settings.jira_api_token,
                timeout_seconds=settings.rovo_automation_timeout_seconds,
                poll_seconds=settings.rovo_automation_poll_seconds,
            )
        return GeminiClient(settings.gemini_api_key)
