# backend/tests/test_security_news_schedule.py
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from src.domain.constants import KST
from src.infrastructure.scheduling.report_scheduler import create_scheduler


class SecurityNewsScheduleTest(unittest.TestCase):
    def test_daily_eight_kst_is_independent_of_report_timezone_without_startup_run(self) -> None:
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_security_news=callback)
        job = scheduler.get_job("security_news_daily")
        self.assertIs(job.func, callback)
        expected = datetime(2026, 10, 24, 8, tzinfo=KST)
        self.assertEqual(expected, job.trigger.get_next_fire_time(None, expected - timedelta(seconds=1)))
        self.assertEqual(expected, job.trigger.get_next_fire_time(None, expected.astimezone(timezone.utc)))
        self.assertEqual(expected + timedelta(days=1), job.trigger.get_next_fire_time(expected, expected))
        self.assertEqual(expected + timedelta(days=1), job.trigger.get_next_fire_time(None, expected + timedelta(seconds=1)))
        self.assertEqual(1, job.max_instances)
        self.assertTrue(job.coalesce)
        self.assertEqual(3600, job.misfire_grace_time)
        self.assertFalse(hasattr(job, "next_run_time"))

    def test_news_callback_is_optional_for_other_scheduler_consumers(self) -> None:
        scheduler = create_scheduler("0 23 * * fri", "Asia/Seoul", AsyncMock())
        self.assertIsNone(scheduler.get_job("security_news_daily"))
