# backend/src/infrastructure/scheduling/report_scheduler.py
import logging
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def _parse_cron(cron_expression: str) -> dict[str, str]:
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("schedule_cron must contain exactly five fields")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def create_scheduler(
    schedule_cron: str,
    timezone: str,
    generate: Callable[[], Awaitable[None]],
    refresh_interval_minutes: int | None = None,
    refresh: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        generate,
        CronTrigger(**_parse_cron(schedule_cron), timezone=timezone),
    )
    logger.info("스케줄러 등록 [보고서 생성]: %s (%s)", schedule_cron, timezone)
    if refresh_interval_minutes and refresh:
        scheduler.add_job(
            refresh,
            IntervalTrigger(minutes=refresh_interval_minutes),
        )
        logger.info(
            "스케줄러 등록 [보고서 자동 갱신]: 매 %d분",
            refresh_interval_minutes,
        )
    return scheduler
