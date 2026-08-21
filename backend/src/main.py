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


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        started = False
        try:
            async with AsyncExitStack() as stack:
                database = Database(settings.database_url)
                stack.push_async_callback(database.aclose)
                container = Container(settings, database)
                stack.push_async_callback(container.aclose)
                audit = AuditLogger()
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
                    jira=container.jira,
                    jira_base_url=container.jira_base_url,
                    project_key=settings.project_key,
                    job_runner=job_runner,
                    partner=container.partner,
                    storage=container.storage,
                    get_report=container.get_report,
                    get_site=container.get_site,
                )
                scheduler = create_scheduler(
                    schedule_cron=settings.schedule_cron,
                    timezone=settings.tz,
                    generate=job_runner.run_scheduled_job,
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
