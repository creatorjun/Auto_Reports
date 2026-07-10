# backend/src/main.py
import logging
import sys
import threading

from contextlib import asynccontextmanager
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.scheduler.report_scheduler import create_scheduler
from src.infrastructure.config.settings import get_settings
from src.infrastructure.container import Container
from src.infrastructure.job_runner import JobRunner
from src.infrastructure.persistence.database import AsyncSessionLocal, close_db, init_db
from src.infrastructure.persistence.job_repository_impl import SqlJobRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def _run_migrations_in_thread() -> None:
    try:
        logger.info("DB 마이그레이션 실행 중...")
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("DB 마이그레이션 완료 ✅")
    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")


def run_migrations() -> None:
    t = threading.Thread(target=_run_migrations_in_thread, daemon=False)
    t.start()
    t.join()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    init_db(settings.database_url)
    logger.info("DB 엔진 초기화 ✅")

    run_migrations()

    container = Container(settings)

    async with AsyncSessionLocal() as session:
        job_repository = SqlJobRepository(session)
        job_runner = JobRunner(container, job_repository)

    app.state.container = container
    app.state.job_runner = job_runner

    scheduler = create_scheduler(
        schedule_cron=settings.schedule_cron,
        tz=settings.tz,
        generate_fn=job_runner.run_scheduled_job,
    )
    scheduler.start()
    logger.info("TAC Auto Reports 서비스 시작 ✅")

    yield

    scheduler.shutdown()
    await container.aclose()
    await close_db()
    logger.info("TAC Auto Reports 서비스 종료")


settings = get_settings()

app = FastAPI(
    title="TAC Auto Reports API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.presentation.api.v1.router import router
app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
