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
from src.shared.audit_logger import get_audit_logger

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

    get_audit_logger()
    logger.info("Audit 로거 초기화 ✅")

    container = Container(settings)

    if AsyncSessionLocal is None:
        raise RuntimeError("DB가 초기화되지 않았습니다.")

    job_repository = SqlJobRepository(AsyncSessionLocal)
    job_runner = JobRunner(
        container=container,
        job_repository=job_repository,
        session_factory=AsyncSessionLocal,
    )

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


app = FastAPI(
    title="TAC Auto Reports API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.presentation.api.v1.router import router
app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
