# backend/src/application/scheduler/report_scheduler.py
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import Settings

logger = logging.getLogger(__name__)


def create_scheduler(settings: Settings, generate_fn) -> AsyncIOScheduler:
    parts = settings.schedule_cron.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3],
        day_of_week=parts[4], timezone=settings.tz
    )
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(generate_fn, trigger)
    logger.info(f"스케줄러 등록: {settings.schedule_cron} ({settings.tz})")
    return scheduler
