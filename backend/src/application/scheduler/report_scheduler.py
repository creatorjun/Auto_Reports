# backend/src/application/scheduler/report_scheduler.py
import logging
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
    refresh_interval_minutes: int | None = None,
    refresh_fn: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    trigger = CronTrigger(**_parse_cron(schedule_cron), timezone=tz)
    scheduler.add_job(generate_fn, trigger)
    logger.info(f"\uc2a4\ucf00\uc904\ub7ec \ub4f1\ub85d [\ubcf4\uace0\uc11c \uc0dd\uc131]: {schedule_cron} ({tz})")

    if refresh_interval_minutes and refresh_fn:
        refresh_trigger = IntervalTrigger(minutes=refresh_interval_minutes)
        scheduler.add_job(refresh_fn, refresh_trigger)
        logger.info(f"\uc2a4\ucf00\uc904\ub7ec \ub4f1\ub85d [\ubcf4\uace0\uc11c \uc790\ub3d9 \uac31\uc2e0]: \ub9e4 {refresh_interval_minutes}\ubd84")

    return scheduler
