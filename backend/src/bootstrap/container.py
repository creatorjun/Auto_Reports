# backend/src/bootstrap/container.py
from contextlib import AsyncExitStack, asynccontextmanager
import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.auth_service import AuthService
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.security_news_translation import SecurityNewsTranslationService
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.get_report_chart_issues import GetReportChartIssuesUseCase
from src.application.use_cases.notify_tac_assigned import NotifyTacAssignedUseCase
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase
from src.application.use_cases.notify_sla_digest import NotifySlaDigestUseCase
from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.use_cases.refresh_report import RefreshReportUseCase
from src.application.use_cases.search import SearchUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.sla_dashboard import SlaDashboardUseCase
from src.application.use_cases.sla_status import SlaStatusUseCase
from src.application.use_cases.jira_notifications import JiraNotificationsUseCase
from src.application.use_cases.sla_violation_report import SlaViolationReportUseCase
from src.application.use_cases.redeployment_report import RedeploymentGenerationInProgress, RedeploymentReportUseCase
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.application.use_cases.security_news import SecurityNewsUseCase
from src.application.use_cases.storage_use_case import StorageUseCase
from src.domain.entities.report import Report
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.smtp_email_client import SmtpEmailClient
from src.infrastructure.external.security_news_source import PublicSecurityNewsSource
from src.infrastructure.external.gemini_news_translator import GeminiNewsTranslator
from src.infrastructure.external.jira_oauth_client import JiraOAuthClient
from src.infrastructure.external.jira_notification_client import JiraNotificationClient
from src.infrastructure.external.sla_violation_jira_source import SlaViolationJiraSource
from src.infrastructure.external.sla_digest_jira_source import SlaDigestJiraSource
from src.infrastructure.external.redeployment_jira_source import RedeploymentJiraSource
from src.infrastructure.factories.ai_factory import AiFactory
from src.infrastructure.factories.jira_factory import JiraFactory
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.issue_management_snapshot_repository import IssueManagementSnapshotRepository
from src.infrastructure.personal_data_runtime import PersonalDataRuntime
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.persistence.security_news_translation_cache import SqliteNewsTranslationCache
from src.infrastructure.persistence.site_repository_impl import SiteRepositoryImpl
from src.infrastructure.persistence.sla_violation_repository_impl import SlaViolationRepositoryImpl
from src.infrastructure.persistence.redeployment_repository_impl import RedeploymentRepositoryImpl
from src.infrastructure.report_cache import ReportLruCache
from src.infrastructure.security.credential_encryptor import CredentialEncryptor
from src.infrastructure.security.jwt_service import JwtService
from src.infrastructure.security.memory_jira_user_grant_store import MemoryJiraUserGrantStore
from src.infrastructure.storage.document_converter import LibreOfficeDocumentConverter
from src.infrastructure.storage.local_storage import LocalStorageAdapter
from src.presentation.email.issue_notification_renderer import IssueNotificationRenderer
from src.presentation.email.sla_digest_renderer import SlaDigestRenderer


class Container:
    def __init__(self, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._database = database
        self._jira = JiraFactory.create(settings)
        self._ai = AiFactory.create(settings)
        self._sla_violation_source = SlaViolationJiraSource(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            project_key=settings.project_key,
            sla_initial_response_field_id=settings.sla_initial_response_field_id,
            sla_resolution_field_id=settings.sla_resolution_field_id,
            tac_assignee_field_id=settings.jira_recent_tac_assignee_field_id,
            resolution_pause_statuses=tuple(settings.sla_resolution_pause_statuses),
        )
        self._sla_violation_generation_lock = asyncio.Lock()
        self._redeployment_source = RedeploymentJiraSource(
            base_url=settings.jira_base_url, email=settings.jira_email,
            api_token=settings.jira_api_token, project_key=settings.project_key,
        )
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
        self._query_builder = query_builder
        self._cache: ReportCachePort = ReportLruCache(maxsize=50)
        self._assembler = ReportAssembler(
            query_builder=query_builder,
            base_collector_factory=collectors.base_collectors,
            monthly_collector_factory=collectors.monthly_collectors,
            annual_collector_factory=collectors.annual_collectors,
            issue_type_provider=lambda: self._jira.get_project_issue_types(settings.project_key),
        )
        self._analyzer = AiAnalyzer(ai=self._ai, enabled=settings.ai_enabled)
        self.personal_data = PersonalDataRuntime(settings, database, self._clear_personal_data_caches)
        tokens = JwtService(settings)
        self._jira_user_grants = MemoryJiraUserGrantStore()
        self._jira_notification_source = JiraNotificationClient(settings.jira_base_url)
        self.jira_notifications = JiraNotificationsUseCase(self._jira_notification_source, self._jira_user_grants)
        self.auth = AuthService(
            tokens=tokens,
            enabled=settings.login,
            admin_username=settings.admin_username,
            admin_password=settings.admin_password,
            superadmin_username=settings.superadmin_username,
            superadmin_password=settings.superadmin_password,
            refresh_expire_days=settings.jwt_refresh_expire_days,
            cookie_secure=settings.cookie_secure,
            personal_data=self.personal_data,
            reporting=self.personal_data,
            jira_grants=self._jira_user_grants,
            privacy_owner_account_id=settings.jira_privacy_owner_account_id,
            jira_oauth=JiraOAuthClient(
                client_id=settings.jira_oauth_client_id,
                client_secret=settings.jira_oauth_client_secret,
                redirect_uri=settings.jira_oauth_redirect_uri,
                jira_base_url=settings.jira_base_url,
                project_key=settings.project_key,
                grants=self._jira_user_grants,
            ) if (
                settings.login and settings.jira_login_enabled
                and settings.jira_oauth_client_id and settings.jira_oauth_client_secret
                and settings.jira_oauth_redirect_uri
            ) else None,
        )
        self.storage = StorageUseCase(
            storage=LocalStorageAdapter(settings.storage_dir),
            converter=LibreOfficeDocumentConverter(),
        )
        self.partner = PartnerUseCase(
            jira=self._jira,
            service_desk=self._jira,
            project_key=settings.project_key,
        )
        self.search = SearchUseCase(self._jira)
        self.issue_management = IssueManagementUseCase(self._jira, "TACEA", IssueManagementSnapshotRepository(database))
        self._security_news_source = PublicSecurityNewsSource()
        self._news_translator = None
        self._news_translation_cache = None
        self._news_translation = None
        if settings.security_news_translation_enabled and settings.gemini_api_key:
            self._news_translator = GeminiNewsTranslator(
                settings.gemini_api_key, settings.security_news_translation_model,
            )
            self._news_translation_cache = SqliteNewsTranslationCache(
                settings.security_news_translation_cache_path,
            )
            self._news_translation = SecurityNewsTranslationService(
                self._news_translator, self._news_translation_cache,
                daily_limit=settings.security_news_translation_daily_request_limit,
                batch_size=settings.security_news_translation_batch_size,
                minimum_interval_seconds=settings.security_news_translation_min_interval_seconds,
                max_attempts=settings.security_news_translation_max_attempts,
            )
        self.security_news = SecurityNewsUseCase(self._security_news_source, translation=self._news_translation)
        self._credential_encryptor = (
            CredentialEncryptor(settings.credential_encryption_key)
            if settings.credential_encryption_key
            else None
        )
        smtp = self._build_smtp(settings)
        notification_renderer = IssueNotificationRenderer()
        self._notify_todo = (
            NotifyTodoIssuesUseCase(
                email=smtp,
                renderer=notification_renderer,
                notify_to=settings.notify_todo_to,
                jira_base_url=settings.jira_base_url,
            )
            if smtp and settings.notify_todo_enabled and settings.notify_todo_to
            else None
        )
        self._sla_status_source = SlaDigestJiraSource(
            base_url=settings.jira_base_url, email=settings.jira_email,
            api_token=settings.jira_api_token, project_key=settings.project_key,
        )
        self.sla_status = SlaStatusUseCase(self._sla_status_source, details=self._sla_violation_source)
        self._sla_digest_source = (
            self._sla_status_source
            if self._notify_todo is not None and settings.notify_sla_digest_enabled
            else None
        )
        self._notify_sla_digest = (
            NotifySlaDigestUseCase(
                source=self._sla_digest_source, email=smtp,
                renderer=SlaDigestRenderer(), notify_to=settings.notify_todo_to,
                jira_base_url=settings.jira_base_url,
            )
            if self._sla_digest_source is not None and smtp is not None
            else None
        )
        self._notify_tac = (
            NotifyTacAssignedUseCase(
                email=smtp,
                renderer=notification_renderer,
                notify_to=settings.notify_tac_to,
                jira_base_url=settings.jira_base_url,
                keyword=settings.notify_tac_keyword,
            )
            if smtp and settings.notify_tac_enabled and settings.notify_tac_to
            else None
        )

    @property
    def jira_base_url(self) -> str:
        return self._settings.jira_base_url

    @property
    def sla_digest_enabled(self) -> bool:
        return self._notify_sla_digest is not None

    @property
    def notify_sla_digest(self) -> NotifySlaDigestUseCase | None:
        return self._notify_sla_digest

    async def send_sla_digest(self) -> int:
        if self._notify_sla_digest is None:
            return 0
        return await self._notify_sla_digest.execute()

    async def _clear_personal_data_caches(self) -> None:
        await self.auth.clear_jira_grants()
        await self.issue_management.clear_personal_data_cache()
        await self._jira.clear_personal_data_cache()
        await self.sla_status.clear_personal_data_cache()
        await self._cache.aclose()

    @asynccontextmanager
    async def get_report(self) -> AsyncIterator[GetReportUseCase]:
        async with self._database.session() as session:
            yield GetReportUseCase(
                ReportRepositoryImpl(session),
                cache=self._cache,
            )

    @asynccontextmanager
    async def get_report_chart_issues(self) -> AsyncIterator[GetReportChartIssuesUseCase]:
        async with self.get_report() as reports:
            yield GetReportChartIssuesUseCase(reports, self._jira, self._query_builder)

    @asynccontextmanager
    async def get_site(self) -> AsyncIterator[SiteUseCase]:
        async with self._database.session() as session:
            yield SiteUseCase(
                SiteRepositoryImpl(session, self._credential_encryptor)
            )

    @asynccontextmanager
    async def get_sla_dashboard(self) -> AsyncIterator[SlaDashboardUseCase]:
        async with self.get_report() as reports:
            yield SlaDashboardUseCase(
                reports=reports,
                jira=self._jira,
                project_key=self._settings.project_key,
            )

    @asynccontextmanager
    async def get_sla_violation(self) -> AsyncIterator[SlaViolationReportUseCase]:
        async with self._database.session() as session:
            yield SlaViolationReportUseCase(
                source=self._sla_violation_source,
                repository=SlaViolationRepositoryImpl(session),
                generation_lock=self._sla_violation_generation_lock,
            )

    @asynccontextmanager
    async def get_redeployment(self) -> AsyncIterator[RedeploymentReportUseCase]:
        async with self._database.session() as session:
            yield RedeploymentReportUseCase(self._redeployment_source, RedeploymentRepositoryImpl(session))

    async def refresh_redeployment_report(self) -> None:
        try:
            async with self.get_redeployment() as use_case:
                report = await use_case.generate("schedule")
            logging.getLogger(__name__).info("재배포 보고서 저장 확인: #%s (%s건)", report.id, len(report.tickets))
        except RedeploymentGenerationInProgress:
            logging.getLogger(__name__).info("재배포 보고서 갱신 진행 중: 중복 실행 생략")

    async def generate_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        *,
        bypass_jira_cache: bool = False,
        force_standard: bool = False,
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
            with self._jira.bypass_cache(enabled=bypass_jira_cache):
                return await use_case.execute(
                    start_date=start_date,
                    end_date=end_date,
                    force_standard=force_standard,
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
        async with AsyncExitStack() as stack:
            stack.push_async_callback(self._jira_notification_source.aclose)
            stack.push_async_callback(self._jira_user_grants.aclose)
            stack.push_async_callback(self._jira.aclose)
            stack.push_async_callback(self._sla_violation_source.aclose)
            stack.push_async_callback(self._sla_status_source.aclose)
            stack.push_async_callback(self.sla_status.aclose)
            stack.push_async_callback(self._redeployment_source.aclose)
            if self._ai is not None:
                stack.push_async_callback(self._ai.aclose)
            stack.push_async_callback(self._cache.aclose)
            stack.push_async_callback(self.issue_management.aclose)
            stack.push_async_callback(self._security_news_source.aclose)
            if self._news_translator is not None:
                stack.push_async_callback(self._news_translator.aclose)
            if self._news_translation_cache is not None:
                stack.push_async_callback(self._news_translation_cache.aclose)
            if self._news_translation is not None:
                stack.push_async_callback(self._news_translation.aclose)
            stack.push_async_callback(self.security_news.aclose)

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
