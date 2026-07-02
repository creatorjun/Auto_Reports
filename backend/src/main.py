# backend/src/main.py
import logging
import sys

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


@asynccontextmanager
async def lifespan(app: FastAPI):
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
