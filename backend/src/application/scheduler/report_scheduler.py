# backend/src/application/scheduler/report_scheduler.py
import logging
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def create_scheduler(
    schedule_cron: str,
    tz: str,
    generate_fn: Callable[[], Awaitable[None]],
) -> AsyncIOScheduler:
    parts = schedule_cron.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3],
        day_of_week=parts[4], timezone=tz,
    )
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(generate_fn, trigger)
    logger.info(f"스케줄러 등록: {schedule_cron} ({tz})")
    return scheduler
