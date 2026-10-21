# backend/src/main.py
import logging
import sys
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.bootstrap.container import Container
from src.application.errors import EntityNotFoundError, JobAlreadyRunningError
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.job_runner import JobRunner
from src.infrastructure.logging.audit_logger import AuditLogger
from src.infrastructure.logging.audit_log_reader import FileAuditLogReader
from src.infrastructure.logging.oauth_access_filter import OAuthAccessFilter
from src.application.use_cases.audit_logs import AuditLogsUseCase
from src.application.use_cases.trigger_report import TriggerReportUseCase
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.job_repository_impl import SqlJobRepository
from src.infrastructure.scheduling.report_scheduler import create_scheduler
from src.presentation.api.deps import ApiServices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").addFilter(OAuthAccessFilter())
logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        started = False
        try:
            async with AsyncExitStack() as stack:
                database = Database(settings.database_url)
                stack.push_async_callback(database.aclose)
                container = await stack.enter_async_context(Container.open(settings, database))
                await container.auth.clear_jira_grants()
                await container.issue_management.initialize()
                await container.security_news.initialize()
                audit = AuditLogger(settings.audit_log_dir)
                stack.callback(audit.close)
                job_repository = SqlJobRepository(database.session_factory)
                job_runner = JobRunner(
                    generate_report=container.generate_report,
                    job_repository=job_repository,
                )
                stack.push_async_callback(job_runner.aclose)
                application.state.services = ApiServices(
                    auth=container.auth,
                    audit=audit,
                    jira_base_url=container.jira_base_url,
                    job_runner=job_runner,
                    trigger_report=TriggerReportUseCase(job_runner, container.get_report),
                    partner=container.partner,
                    search=container.search,
                    storage=container.storage,
                    get_report=container.get_report,
                    get_site=container.get_site,
                    get_sla_dashboard=container.get_sla_dashboard,
                    get_sla_violation=container.get_sla_violation,
                    get_redeployment=container.get_redeployment,
                    get_report_chart_issues=container.get_report_chart_issues,
                    issue_management=container.issue_management,
                    security_news=container.security_news,
                    audit_logs=AuditLogsUseCase(FileAuditLogReader(settings.audit_log_dir)),
                    notify_sla_digest=container.notify_sla_digest,
                    sla_status=container.sla_status,
                    jira_notifications=container.jira_notifications,
                )
                scheduler = create_scheduler(
                    schedule_cron=settings.schedule_cron,
                    timezone=settings.tz,
                    generate=job_runner.run_scheduled_job,
                    refresh_redeployments=container.refresh_redeployment_report,
                    refresh_security_news=container.security_news.refresh_scheduled,
                    report_personal_data=container.personal_data.run_reporting,
                    notify_sla_digest=(
                        container.send_sla_digest if container.sla_digest_enabled else None
                    ),
                    refresh_interval_minutes=(
                        settings.refresh_report_interval_minutes
                        if settings.refresh_report_enabled
                        else None
                    ),
                    refresh=(
                        container.refresh_report
                        if settings.refresh_report_enabled
                        else None
                    ),
                )
                scheduler.start()
                stack.callback(scheduler.shutdown, wait=False)
                sla_digest_job = scheduler.get_job("sla_digest_daily")
                if sla_digest_job is not None:
                    logger.info("SLA 일일 메일 다음 실행: %s", sla_digest_job.next_run_time.isoformat())
                started = True
                logger.info("TAC Auto Reports 서비스 시작")
                yield
        finally:
            if started:
                logger.info("TAC Auto Reports 서비스 종료")

    application = FastAPI(
        title="TAC Auto Reports API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(EntityNotFoundError)
    async def handle_not_found(
        request: Request,
        error: EntityNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(JobAlreadyRunningError)
    async def handle_job_conflict(
        request: Request,
        error: JobAlreadyRunningError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": (
                    "이미 실행 중인 보고서 생성 작업이 있습니다. "
                    f"(job_id={error.job_id})"
                )
            },
        )

    from src.presentation.api.v1.router import router

    application.include_router(router)

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app(get_settings())
