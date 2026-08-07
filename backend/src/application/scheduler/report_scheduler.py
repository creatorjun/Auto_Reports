# backend/src/application/scheduler/report_scheduler.py
import logging
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _parse_cron(cron_expr: str) -> dict:
    parts = cron_expr.split()
    return dict(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )


def create_scheduler(
    schedule_cron: str,
    tz: str,
    generate_fn: Callable[[], Awaitable[None]],
    notify_cron: str | None = None,
    notify_fn: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    trigger = CronTrigger(**_parse_cron(schedule_cron), timezone=tz)
    scheduler.add_job(generate_fn, trigger)
    logger.info(f"스케줄러 등록 [보고서 생성]: {schedule_cron} ({tz})")

    if notify_cron and notify_fn:
        notify_trigger = CronTrigger(**_parse_cron(notify_cron), timezone=tz)
        scheduler.add_job(notify_fn, notify_trigger)
        logger.info(f"스케줄러 등록 [할일 알림]: {notify_cron} ({tz})")

    return scheduler
