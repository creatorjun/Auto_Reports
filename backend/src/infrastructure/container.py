# backend/src/infrastructure/container.py
import logging
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase
from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.use_cases.site_use_cases import SiteUseCase
from src.application.use_cases.storage_use_case import StorageUseCase
from src.domain.ports.jira_port import JiraPort
from src.domain.ports.service_desk_port import ServiceDeskPort
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.external.smtp_email_client import SmtpEmailClient
from src.infrastructure.factories.ai_factory import AiFactory
from src.infrastructure.factories.jira_factory import JiraFactory
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.persistence.site_repository_impl import SiteRepositoryImpl
from src.infrastructure.report_cache import ReportLruCache
from src.infrastructure.security.credential_encryptor import CredentialEncryptor
from src.infrastructure.security.jwt_service import JwtService
from src.infrastructure.storage.local_storage import LocalStorageAdapter

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._jira: JiraClient = JiraFactory.create(settings)
        self._ai = AiFactory.create(settings)
        self._collector_factory = WidgetCollectorFactory(self._jira)
        self._query_config = QueryConfig(
            project_key=settings.project_key,
            issue_types=settings.issue_types,
            active_statuses=settings.active_statuses,
            closed_statuses=settings.closed_statuses,
            sla_threshold_days=settings.sla_threshold_days,
            year_start=settings.year_start,
        )
        self._report_cache: ReportCachePort = ReportLruCache(maxsize=50)
        self._query_builder = WidgetQueryBuilder(self._query_config)
        self._assembler = ReportAssembler(
            query_builder=self._query_builder,
            base_collector_factory=self._collector_factory.base_collectors,
            monthly_collector_factory=self._collector_factory.monthly_collectors,
        )
        self._analyzer = AiAnalyzer(
            ai=self._ai,
            enabled=settings.ai_enabled,
        )
        self._jwt_service = JwtService(settings)
        self._storage_use_case = StorageUseCase(
            LocalStorageAdapter(settings.storage_dir)
        )
        self._partner_use_case = PartnerUseCase(
            jira=self._jira,
            service_desk=self._jira,
            project_key=settings.project_key,
            tac_assignee_fid=settings.jira_tac_assignee_field_id,
            qa_assignee_fid=settings.jira_qa_assignee_field_id,
        )
        self._credential_encryptor: CredentialEncryptor | None = (
            CredentialEncryptor(settings.credential_encryption_key)
            if settings.credential_encryption_key
            else None
        )

        self._notify_todo_use_case: NotifyTodoIssuesUseCase | None = None
        if settings.notify_todo_enabled and settings.smtp_host and settings.notify_todo_to:
            smtp_client = SmtpEmailClient(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                from_addr=settings.smtp_from or settings.smtp_user,
                use_tls=settings.smtp_use_tls,
                start_tls=settings.smtp_start_tls,
            )
            self._notify_todo_use_case = NotifyTodoIssuesUseCase(
                jira=self._jira,
                email=smtp_client,
                project_key=settings.project_key,
                issue_types=settings.issue_types,
                closed_statuses=settings.closed_statuses,
                notify_to=settings.notify_todo_to,
                jira_base_url=settings.jira_base_url,
            )
            logger.info(f"할일 알림 활성화: {settings.notify_todo_to}")
        else:
            logger.info("할일 알림 비활성화 (NOTIFY_TODO_ENABLED=false 또는 SMTP 미설정)")

    @property
    def login_enabled(self) -> bool:
        return self._settings.login

    @property
    def cookie_secure(self) -> bool:
        return self._settings.cookie_secure

    @property
    def jira_base_url(self) -> str:
        return self._settings.jira_base_url

    @property
    def superadmin_username(self) -> str:
        return self._settings.superadmin_username

    @property
    def jwt_refresh_expire_days(self) -> int:
        return self._settings.jwt_refresh_expire_days

    def is_valid_credentials(self, username: str, password: str) -> bool:
        if not password:
            return False
        s = self._settings
        if username == s.admin_username and password == s.admin_password:
            return True
        return self.is_superadmin(username, password)

    def is_superadmin(self, username: str, password: str) -> bool:
        s = self._settings
        return bool(
            s.superadmin_username
            and username == s.superadmin_username
            and password == s.superadmin_password
        )

    def jwt_service(self) -> JwtService:
        return self._jwt_service

    def storage_use_case(self) -> StorageUseCase:
        return self._storage_use_case

    def jira_port(self) -> JiraPort:
        return self._jira

    def service_desk_port(self) -> ServiceDeskPort:
        return self._jira

    def partner_use_case(self) -> PartnerUseCase:
        return self._partner_use_case

    def notify_todo_use_case(self) -> NotifyTodoIssuesUseCase | None:
        return self._notify_todo_use_case

    async def aclose(self) -> None:
        await self._jira.aclose()
        logger.info("JiraClient 커넥션 풀 종료")

    def generate_report_use_case(self, session: AsyncSession) -> GenerateReportUseCase:
        return GenerateReportUseCase(
            assembler=self._assembler,
            analyzer=self._analyzer,
            repository=ReportRepositoryImpl(session),
            cache=self._report_cache,
            retention_weeks=self._settings.report_retention_weeks,
        )

    def get_report_use_case(self, session: AsyncSession) -> GetReportUseCase:
        repo = ReportRepositoryImpl(session)
        return GetReportUseCase(repo, cache=self._report_cache)

    def site_use_case(self, session: AsyncSession) -> SiteUseCase:
        repo = SiteRepositoryImpl(session, self._credential_encryptor)
        return SiteUseCase(repo)
