# backend/src/infrastructure/scheduling/report_scheduler.py
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from src.domain.constants import KST

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
    refresh_redeployments: Callable[[], Awaitable[None]] | None = None,
    report_personal_data: Callable[[], Awaitable[dict]] | None = None,
    notify_sla_digest: Callable[[], Awaitable[int]] | None = None,
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
    if refresh_redeployments:
        scheduler.add_job(
            refresh_redeployments,
            CronTrigger(hour=8, minute=0, timezone="Asia/Seoul"),
            id="redeployment_daily", name="재배포 이슈 매일 08:00 KST",
            next_run_time=datetime.now(KST), coalesce=True, max_instances=1,
            misfire_grace_time=3600,
        )
        logger.info("스케줄러 등록 [재배포 이슈]: 매일 08:00 KST, 시작 시 누락된 보고서 갱신")
    if report_personal_data:
        scheduler.add_job(
            report_personal_data, IntervalTrigger(minutes=5, jitter=30),
            id="personal_data_reporting", name="Atlassian 개인정보 보고",
            next_run_time=datetime.now(KST), coalesce=True, max_instances=1,
            misfire_grace_time=3600,
        )
    if notify_sla_digest:
        scheduler.add_job(
            notify_sla_digest,
            CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
            id="sla_digest_daily", name="SLA 일일 요약 매일 09:00 KST",
            coalesce=True, max_instances=1, misfire_grace_time=3600,
        )
        logger.info("스케줄러 등록 [SLA 일일 요약]: 매일 09:00 KST")
    return scheduler
