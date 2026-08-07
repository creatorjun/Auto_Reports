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
        logger.info("DB \uc5d4\uc9c4 \ucd08\uae30\ud654 \u2705")

        if db_module.AsyncSessionLocal is None:
            raise RuntimeError("DB\uac00 \ucd08\uae30\ud654\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.")

        get_audit_logger()
        logger.info("Audit \ub85c\uac70 \ucd08\uae30\ud654 \u2705")

        container = Container(settings)

        job_repository = SqlJobRepository(db_module.AsyncSessionLocal)
        job_runner = JobRunner(
            container=container,
            job_repository=job_repository,
            session_factory=db_module.AsyncSessionLocal,
        )

        app.state.container = container
        app.state.job_runner = job_runner

        async def _refresh_fn() -> None:
            async with db_module.AsyncSessionLocal() as session:
                uc = container.refresh_report_use_case(session)
                await uc.execute()
                await session.commit()

        scheduler = create_scheduler(
            schedule_cron=settings.schedule_cron,
            tz=settings.tz,
            generate_fn=job_runner.run_scheduled_job,
            refresh_interval_minutes=(
                settings.refresh_report_interval_minutes
                if settings.refresh_report_enabled
                else None
            ),
            refresh_fn=_refresh_fn if settings.refresh_report_enabled else None,
        )
        scheduler.start()
        logger.info("TAC Auto Reports \uc11c\ube44\uc2a4 \uc2dc\uc791 \u2705")

        yield

        scheduler.shutdown()
        await container.aclose()
        await close_db()
        logger.info("TAC Auto Reports \uc11c\ube44\uc2a4 \uc885\ub8cc")

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
