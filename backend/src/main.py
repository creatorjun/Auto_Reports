# backend/src/main.py
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.scheduler.report_scheduler import create_scheduler
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.container import Container
from src.infrastructure.job_runner import JobRunner
import src.infrastructure.persistence.database as db_module
from src.infrastructure.persistence.database import close_db, init_db
from src.infrastructure.persistence.job_repository_impl import SqlJobRepository
from src.shared.audit_logger import get_audit_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(settings.database_url)
        logger.info("DB 엔진 초기화 ✅")

        if db_module.AsyncSessionLocal is None:
            raise RuntimeError("DB가 초기화되지 않았습니다.")

        get_audit_logger()
        logger.info("Audit 로거 초기화 ✅")

        container = Container(settings)

        job_repository = SqlJobRepository(db_module.AsyncSessionLocal)
        job_runner = JobRunner(
            container=container,
            job_repository=job_repository,
            session_factory=db_module.AsyncSessionLocal,
        )

        app.state.container = container
        app.state.job_runner = job_runner

        notify_use_case = container.notify_todo_use_case()
        notify_fn = notify_use_case.execute if notify_use_case is not None else None

        async def _refresh_fn() -> None:
            async with db_module.AsyncSessionLocal() as session:
                uc = container.refresh_report_use_case(session)
                await uc.execute()
                await session.commit()

        scheduler = create_scheduler(
            schedule_cron=settings.schedule_cron,
            tz=settings.tz,
            generate_fn=job_runner.run_scheduled_job,
            notify_cron=settings.notify_todo_cron if notify_fn else None,
            notify_fn=notify_fn,
            refresh_interval_minutes=(
                settings.refresh_report_interval_minutes
                if settings.refresh_report_enabled
                else None
            ),
            refresh_fn=_refresh_fn if settings.refresh_report_enabled else None,
        )
        scheduler.start()
        logger.info("TAC Auto Reports 서비스 시작 ✅")

        yield

        scheduler.shutdown()
        await container.aclose()
        await close_db()
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

    from src.presentation.api.v1.router import router
    application.include_router(router)

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    return application


app = create_app(get_settings())
