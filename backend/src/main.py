# backend/src/main.py
import logging
import sys
import subprocess

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.scheduler.report_scheduler import create_scheduler
from src.config.settings import get_settings
from src.infrastructure.container import Container
from src.presentation.api.deps import set_container
from src.presentation.api.v1.router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_migrations():
    """앱 시작 시 alembic 마이그레이션 자동 실행"""
    try:
        logger.info("DB 마이그레이션 실행 중...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            logger.info("DB 마이그레이션 완료 ✅")
        else:
            logger.error(f"마이그레이션 실패: {result.stderr}")
    except Exception as e:
        logger.error(f"마이그레이션 예외: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()

    settings = get_settings()
    container = Container(settings)
    set_container(container)

    async def _scheduled_job():
        from src.infrastructure.persistence.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            uc = container.generate_report_use_case(session)
            await uc.execute()

    scheduler = create_scheduler(settings, _scheduled_job)
    scheduler.start()
    logger.info("TAC Auto Reports 서비스 시작 ✅")
    yield
    scheduler.shutdown()
    logger.info("TAC Auto Reports 서비스 종료")


app = FastAPI(
    title="TAC Auto Reports API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
