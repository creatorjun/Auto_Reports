# backend/src/infrastructure/container.py
import logging
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.config.settings import Settings
from src.domain.ports.ai_port import AiPort
from src.domain.ports.jira_port import JiraPort
from src.infrastructure.external.gemini_client import GeminiClient
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.persistence.database import AsyncSessionLocal
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._jira: JiraPort = JiraClient(
            settings.jira_base_url,
            settings.jira_email,
            settings.jira_api_token,
        )
        self._ai: AiPort | None = GeminiClient(settings.gemini_api_key) if settings.ai_enabled else None
        self._jobs: dict[str, dict] = {}

    async def aclose(self) -> None:
        await self._jira.aclose()
        logger.info("JiraClient 커넥션 풀 종료")

    def get_job_status(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def generate_report_use_case(self, session: AsyncSession) -> GenerateReportUseCase:
        repo = ReportRepositoryImpl(session)
        query_builder = WidgetQueryBuilder(self._settings)
        assembler = ReportAssembler(
            jira=self._jira,
            query_builder=query_builder,
            sla_threshold_days=self._settings.sla_threshold_days,
            sla_initial_response_field_id=self._settings.sla_initial_response_field_id,
            sla_resolution_field_id=self._settings.sla_resolution_field_id,
        )
        analyzer = AiAnalyzer(
            ai=self._ai,
            enabled=self._settings.ai_enabled,
        )
        return GenerateReportUseCase(assembler, analyzer, repo)

    def get_report_use_case(self, session: AsyncSession) -> GetReportUseCase:
        repo = ReportRepositoryImpl(session)
        return GetReportUseCase(repo)

    async def execute_in_background(self, job_id: str) -> None:
        self._jobs[job_id] = {"status": "running", "report_id": None, "error": None}
        try:
            async with AsyncSessionLocal() as session:
                uc = self.generate_report_use_case(session)
                report = await uc.execute()
            self._jobs[job_id] = {"status": "done", "report_id": report.id, "error": None}
            logger.info(f"[job:{job_id}] 완료 report_id={report.id}")
        except Exception as e:
            self._jobs[job_id] = {"status": "error", "report_id": None, "error": str(e)}
            logger.error(f"[job:{job_id}] 실패: {e}")

    async def run_scheduled_job(self) -> None:
        job_id = str(uuid.uuid4())
        logger.info(f"스케줄 실행 [job:{job_id}]")
        await self.execute_in_background(job_id)
