# backend/src/infrastructure/container.py
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.ai_analyzer import AiAnalyzer
from src.application.services.query_builder import ResolvedQueries, WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.application.widgets.collector_factory import CollectorEntry
from src.application.widgets.count_collector import (
    SimpleCountCollector,
    SimpleWithDetailsCollector,
    SlaMetVsViolatedCollector,
)
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.monthly_collector import MonthlyCollector
from src.application.widgets.monthly_count_collector import MonthlyCountCollector
from src.application.widgets.recent_collector import RecentCollector
from src.application.widgets.resolution_collector import ResolutionCollector
from src.application.widgets.sla_delay_collector import SlaDelayCollector
from src.domain.ports.ai_port import AiPort
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.gemini_client import GeminiClient
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.report_cache import ReportLruCache

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")

_JIRA_FIELDS_COMMON = "summary,issuetype,status,created,resolutiondate"

_CACHE_FRESH_TTL  = 600.0
_CACHE_STALE_TTL  = 120.0


class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._jira: JiraPort = JiraClient(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            sla_initial_response_field_id=settings.sla_initial_response_field_id,
            sla_resolution_field_id=settings.sla_resolution_field_id,
            jira_tac_assignee_field_id=settings.jira_tac_assignee_field_id,
            jira_qa_assignee_field_id=settings.jira_qa_assignee_field_id,
        )
        self._ai: AiPort | None = GeminiClient(settings.gemini_api_key) if settings.ai_enabled else None
        self._query_config = QueryConfig(
            project_key=settings.project_key,
            issue_types=settings.issue_types,
            active_statuses=settings.active_statuses,
            closed_statuses=settings.closed_statuses,
            sla_threshold_days=settings.sla_threshold_days,
            year_start=settings.year_start,
        )
        self._report_cache: ReportCachePort = ReportLruCache(
            maxsize=50,
            ttl_seconds=_CACHE_FRESH_TTL,
            stale_ttl_seconds=_CACHE_STALE_TTL,
        )

    def jira_port(self) -> JiraPort:
        return self._jira

    def _base_collector_factory(self, q: ResolvedQueries, now: datetime) -> list[CollectorEntry]:
        jira = self._jira
        return [
            CollectorEntry(WidgetId.YEARLY_CREATED,      SimpleCountCollector(jira, f"{now.year}년 누적 생성", q.w1_yearly_created())),
            CollectorEntry(WidgetId.YEARLY_RESOLVED,     SimpleCountCollector(jira, f"{now.year}년 누적 해결", q.w2_yearly_resolved())),
            CollectorEntry(WidgetId.CREATED_VS_RESOLVED, CreatedVsResolvedCollector(jira, q)),
            CollectorEntry(WidgetId.ISSUE_REVIEW,        SimpleWithDetailsCollector(jira, "이슈 리뷷 중", q.w4_issue_review())),
            CollectorEntry(WidgetId.DATA_REQUEST,        SimpleWithDetailsCollector(jira, "자료 요청 중", q.w5_data_request())),
            CollectorEntry(WidgetId.RESULT_PENDING,      SimpleWithDetailsCollector(jira, "결과 대기 중", q.w6_result_pending())),
            CollectorEntry(WidgetId.SLA_MET_VS_VIOLATED, SlaMetVsViolatedCollector(jira, q)),
            CollectorEntry(WidgetId.SLA_DELAY_REASON,    SlaDelayCollector(jira, q)),
            CollectorEntry(WidgetId.AVG_RESOLUTION_TYPE, ResolutionCollector(jira, q)),
            CollectorEntry(WidgetId.RECENT_ISSUES,       RecentCollector(jira, q)),
        ]

    def _monthly_collector_factory(self, q: ResolvedQueries, now: datetime) -> list[tuple[WidgetId, object]]:
        jira = self._jira
        return [
            (WidgetId.SLA_INITIAL_RESPONSE, MonthlyCollector(jira, q, now)),
            (WidgetId.MONTHLY_CREATED,      MonthlyCountCollector(jira, q, now)),
        ]

    async def aclose(self) -> None:
        await self._jira.aclose()
        logger.info("JiraClient 콘넥션 풀 종료")

    def generate_report_use_case(self, session: AsyncSession) -> GenerateReportUseCase:
        repo = ReportRepositoryImpl(session)
        query_builder = WidgetQueryBuilder(self._query_config)
        assembler = ReportAssembler(
            query_builder=query_builder,
            base_collector_factory=self._base_collector_factory,
            monthly_collector_factory=self._monthly_collector_factory,
        )
        analyzer = AiAnalyzer(
            ai=self._ai,
            enabled=self._settings.ai_enabled,
        )
        return GenerateReportUseCase(
            assembler=assembler,
            analyzer=analyzer,
            repository=repo,
            cache=self._report_cache,
            retention_weeks=self._settings.report_retention_weeks,
        )

    def get_report_use_case(self, session: AsyncSession) -> GetReportUseCase:
        repo = ReportRepositoryImpl(session)
        return GetReportUseCase(repo, cache=self._report_cache)
