# backend/tests/test_cve_inventory_schedule.py
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock

from src.infrastructure.scheduling.report_scheduler import create_scheduler


class CveInventoryScheduleTest(unittest.TestCase):
    def test_inventory_refresh_has_independent_two_hour_interval(self):
        callback = AsyncMock()
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock(), refresh_cve_inventory=callback)
        job = scheduler.get_job("cve_inventory_refresh")
        self.assertIs(callback, job.func)
        self.assertEqual(timedelta(hours=2), job.trigger.interval)
        self.assertEqual(1, job.max_instances)
        self.assertTrue(job.coalesce)
        self.assertFalse(hasattr(job, "next_run_time"))

    def test_callback_is_optional(self):
        scheduler = create_scheduler("0 23 * * fri", "UTC", AsyncMock())
        self.assertIsNone(scheduler.get_job("cve_inventory_refresh"))
