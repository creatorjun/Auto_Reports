# backend/src/bootstrap/container.py
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from src.application.ports.jira_port import JiraPort
from src.application.ports.report_cache_port import ReportCachePort
from src.application.ports.service_desk_port import ServiceDeskPort
from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.auth_service import AuthService
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.notify_tac_assigned import NotifyTacAssignedUseCase
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase
from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.use_cases.refresh_report import RefreshReportUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.storage_use_case import StorageUseCase
from src.domain.entities.report import Report
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.smtp_email_client import SmtpEmailClient
from src.infrastructure.factories.ai_factory import AiFactory
from src.infrastructure.factories.jira_factory import JiraFactory
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.persistence.site_repository_impl import SiteRepositoryImpl
from src.infrastructure.report_cache import ReportLruCache
from src.infrastructure.security.credential_encryptor import CredentialEncryptor
from src.infrastructure.security.jwt_service import JwtService
from src.infrastructure.storage.document_converter import LibreOfficeDocumentConverter
from src.infrastructure.storage.local_storage import LocalStorageAdapter

class Container:
    def __init__(self, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._database = database
        self._jira = JiraFactory.create(settings)
        ai = AiFactory.create(settings)
        collectors = WidgetCollectorFactory(self._jira)
        query_builder = WidgetQueryBuilder(
            QueryConfig(
                project_key=settings.project_key,
                issue_types=settings.issue_types,
                active_statuses=settings.active_statuses,
                closed_statuses=settings.closed_statuses,
                sla_threshold_days=settings.sla_threshold_days,
                year_start=settings.year_start,
            )
        )
        self._cache: ReportCachePort = ReportLruCache(maxsize=50)
        self._assembler = ReportAssembler(
            query_builder=query_builder,
            base_collector_factory=collectors.base_collectors,
            monthly_collector_factory=collectors.monthly_collectors,
            issue_type_provider=lambda: self._jira.get_project_issue_types(settings.project_key),
        )
        self._analyzer = AiAnalyzer(ai=ai, enabled=settings.ai_enabled)
        tokens = JwtService(settings)
        self.auth = AuthService(
            tokens=tokens,
            enabled=settings.login,
            admin_username=settings.admin_username,
            admin_password=settings.admin_password,
            superadmin_username=settings.superadmin_username,
            superadmin_password=settings.superadmin_password,
            refresh_expire_days=settings.jwt_refresh_expire_days,
            cookie_secure=settings.cookie_secure,
        )
        self.storage = StorageUseCase(
            storage=LocalStorageAdapter(settings.storage_dir),
            converter=LibreOfficeDocumentConverter(),
        )
        self.partner = PartnerUseCase(
            jira=self._jira,
            service_desk=self._jira,
            project_key=settings.project_key,
            tac_assignee_fid=settings.jira_tac_assignee_field_id,
            qa_assignee_fid=settings.jira_qa_assignee_field_id,
        )
        self._credential_encryptor = (
            CredentialEncryptor(settings.credential_encryption_key)
            if settings.credential_encryption_key
            else None
        )
        smtp = self._build_smtp(settings)
        self._notify_todo = (
            NotifyTodoIssuesUseCase(
                email=smtp,
                notify_to=settings.notify_todo_to,
                jira_base_url=settings.jira_base_url,
            )
            if smtp and settings.notify_todo_enabled and settings.notify_todo_to
            else None
        )
        self._notify_tac = (
            NotifyTacAssignedUseCase(
                email=smtp,
                notify_to=settings.notify_tac_to,
                jira_base_url=settings.jira_base_url,
                keyword=settings.notify_tac_keyword,
            )
            if smtp and settings.notify_tac_enabled and settings.notify_tac_to
            else None
        )

    @property
    def jira(self) -> JiraPort:
        return self._jira

    @property
    def service_desk(self) -> ServiceDeskPort:
        return self._jira

    @property
    def jira_base_url(self) -> str:
        return self._settings.jira_base_url

    @asynccontextmanager
    async def get_report(self) -> AsyncIterator[GetReportUseCase]:
        async with self._database.session() as session:
            yield GetReportUseCase(
                ReportRepositoryImpl(session),
                cache=self._cache,
            )

    @asynccontextmanager
    async def get_site(self) -> AsyncIterator[SiteUseCase]:
        async with self._database.session() as session:
            yield SiteUseCase(
                SiteRepositoryImpl(session, self._credential_encryptor)
            )

    async def generate_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Report:
        async with self._database.session() as session:
            use_case = GenerateReportUseCase(
                assembler=self._assembler,
                analyzer=self._analyzer,
                repository=ReportRepositoryImpl(session),
                cache=self._cache,
                retention_weeks=self._settings.report_retention_weeks,
                notify=self._notify_todo,
                notify_tac=self._notify_tac,
            )
            return await use_case.execute(
                start_date=start_date,
                end_date=end_date,
            )

    async def refresh_report(self) -> None:
        async with self._database.session() as session:
            use_case = RefreshReportUseCase(
                assembler=self._assembler,
                repository=ReportRepositoryImpl(session),
                cache=self._cache,
                notify=self._notify_todo,
                notify_tac=self._notify_tac,
            )
            await use_case.execute()

    async def aclose(self) -> None:
        await self._cache.aclose()
        await self._jira.aclose()

    @staticmethod
    def _build_smtp(settings: Settings) -> SmtpEmailClient | None:
        if not settings.smtp_host:
            return None
        return SmtpEmailClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.smtp_from or settings.smtp_user,
            use_tls=settings.smtp_use_tls,
            start_tls=settings.smtp_start_tls,
        )
