# backend/tests/test_sla_digest_schedule.py
import unittest
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.domain.constants import KST
from src.infrastructure.config.settings import Settings
from src.infrastructure.scheduling.report_scheduler import create_scheduler


class SlaDigestScheduleTest(unittest.TestCase):
    def test_daily_nine_kst_is_independent_of_report_schedule_and_timezone(self) -> None:
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), notify_sla_digest=callback)
        job = scheduler.get_job("sla_digest_daily")
        self.assertIs(job.func, callback)
        expected = datetime(2026, 10, 24, 9, tzinfo=KST)
        self.assertEqual(expected, job.trigger.get_next_fire_time(None, expected - timedelta(seconds=1)))
        self.assertEqual(expected, job.trigger.get_next_fire_time(None, expected.astimezone(timezone.utc)))
        self.assertEqual(expected + timedelta(days=1), job.trigger.get_next_fire_time(expected, expected))
        self.assertEqual(1, job.max_instances)
        self.assertTrue(job.coalesce)
        self.assertEqual(3600, job.misfire_grace_time)
        self.assertFalse(hasattr(job, "next_run_time"))

    def test_disabled_digest_does_not_register_job(self) -> None:
        scheduler = create_scheduler("0 23 * * fri", "Asia/Seoul", AsyncMock())
        self.assertIsNone(scheduler.get_job("sla_digest_daily"))

    def test_default_enabled_and_environment_override(self) -> None:
        values = dict(jira_base_url="https://jira.example.test", jira_email="test", jira_api_token="test", _env_file=None)
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(Settings(**values).notify_sla_digest_enabled)
        with patch.dict(os.environ, {"NOTIFY_SLA_DIGEST_ENABLED": "false"}):
            self.assertFalse(Settings(**values).notify_sla_digest_enabled)
