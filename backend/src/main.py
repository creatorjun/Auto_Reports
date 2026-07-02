# backend/src/main.py
import logging
import sys

from contextlib import asynccontextmanager
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.scheduler.report_scheduler import create_scheduler
from src.config.settings import get_settings
from src.infrastructure.container import Container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_migrations() -> None:
    try:
        logger.info("DB 마이그레이션 실행 중...")
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("DB 마이그레이션 완료 ✅")
    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()

    settings = get_settings()
    container = Container(settings)
    app.state.container = container

    scheduler = create_scheduler(settings, container.run_scheduled_job)
    scheduler.start()
    logger.info("TAC Auto Reports 서비스 시작 ✅")
    yield
    scheduler.shutdown()
    logger.info("TAC Auto Reports 서비스 종료")


settings = get_settings()

app = FastAPI(
    title="TAC Auto Reports API",
    version="1.0.0",
    lifespan=lifespan
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
