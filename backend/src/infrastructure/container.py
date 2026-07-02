# backend/src/infrastructure/container.py
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.report_collector import ReportCollector
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.config.settings import Settings
from src.infrastructure.external.gemini_client import GeminiClient
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl


class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._jira = JiraClient(
            settings.jira_base_url,
            settings.jira_email,
            settings.jira_api_token
        )
        self._gemini = GeminiClient(settings.gemini_api_key) if settings.ai_enabled else None

    def generate_report_use_case(self, session: AsyncSession) -> GenerateReportUseCase:
        repo = ReportRepositoryImpl(session)
        query_builder = WidgetQueryBuilder(self._settings)
        collector = ReportCollector(self._jira, query_builder, self._settings)
        analyzer = AiAnalyzer(
            gemini=self._gemini,
            enabled=self._settings.ai_enabled
        )
        return GenerateReportUseCase(collector, analyzer, repo)

    def get_report_use_case(self, session: AsyncSession) -> GetReportUseCase:
        repo = ReportRepositoryImpl(session)
        return GetReportUseCase(repo)
