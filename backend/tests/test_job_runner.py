# backend/tests/test_job_runner.py
import asyncio
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.job_repository import JobRepository
from src.domain.entities.job import JobRecord, JobStatus
from src.domain.entities.report import Report
from src.infrastructure.job_runner import JobRunner


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self.records: dict[str, JobRecord] = {}

    async def save(self, record: JobRecord) -> None:
        self.records[record.job_id] = record

    async def find(self, job_id: str) -> JobRecord | None:
        return self.records.get(job_id)


class JobRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = InMemoryJobRepository()
        self.cache_modes: list[bool] = []
        self.standard_modes: list[bool] = []

        async def generate(
            start: datetime.datetime | None,
            end: datetime.datetime | None,
            *,
            bypass_jira_cache: bool = False,
            force_standard: bool = False,
        ) -> Report:
            self.cache_modes.append(bypass_jira_cache)
            self.standard_modes.append(force_standard)
            return Report(
                id=1,
                week_start=datetime.date(2026, 8, 3),
                week_end=datetime.date(2026, 8, 9),
                report_date="2026-08-09",
            )

        self.runner = JobRunner(generate, self.repository)

    async def test_notification_is_not_lost_before_waiter_starts(self) -> None:
        await self.runner.submit("job-1")
        await asyncio.wait_for(
            self.runner.wait_for_update("job-1", JobStatus.PENDING, timeout=1),
            timeout=0.1,
        )

    async def test_job_reaches_done_state(self) -> None:
        await self.runner.submit("job-2")
        record = None
        for _ in range(20):
            record = await self.runner.get_job_status("job-2")
            if record is not None and record.status == JobStatus.DONE:
                break
            await asyncio.sleep(0)
        self.assertIsNotNone(record)
        self.assertEqual(JobStatus.DONE, record.status)
        self.assertEqual(1, record.report_id)

    async def asyncTearDown(self) -> None:
        await self.runner.aclose()

    async def test_manual_job_bypasses_jira_cache(self) -> None:
        await self.runner.submit("manual", bypass_jira_cache=True)
        await self.runner.wait_for_update("manual", JobStatus.PENDING, timeout=1)
        self.assertEqual([True], self.cache_modes)

    async def test_scheduled_job_preserves_jira_cache(self) -> None:
        await self.runner.run_scheduled_job()
        await asyncio.sleep(0)
        self.assertEqual([False], self.cache_modes)
        self.assertEqual([False], self.standard_modes)

    async def test_dashboard_job_preserves_standard_widget_mode(self) -> None:
        await self.runner.submit("dashboard-year", bypass_jira_cache=True, force_standard=True)
        await self.runner.wait_for_update("dashboard-year", JobStatus.PENDING, timeout=1)
        self.assertEqual([True], self.cache_modes)
        self.assertEqual([True], self.standard_modes)

    async def test_cancelled_pending_submission_releases_slot_for_next_report(self) -> None:
        entered = asyncio.Event()
        save = self.repository.save

        async def save_pending(record):
            if record.job_id == "cancelled" and record.status == JobStatus.PENDING:
                entered.set()
                await asyncio.Event().wait()
            await save(record)

        self.repository.save = save_pending
        submission = asyncio.create_task(self.runner.submit("cancelled"))
        await entered.wait()
        submission.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await submission
        self.assertIsNone(self.runner._running_job_id)
        self.assertFalse(self.runner._tasks)
        self.assertEqual([], self.cache_modes)
        await self.runner.submit("next")
        await asyncio.gather(*self.runner._tasks)
        record = await self.runner.get_job_status("next")
        self.assertEqual(JobStatus.DONE, record.status)
        self.assertEqual(1, record.report_id)

    async def test_close_cancels_tracked_job_and_releases_slot(self) -> None:
        entered = asyncio.Event()

        async def generate(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        self.runner._generate_report = generate
        await self.runner.submit("running")
        await entered.wait()
        await self.runner.aclose()
        record = await self.runner.get_job_status("running")
        self.assertEqual(JobStatus.ERROR, record.status)
        self.assertIsNone(self.runner._running_job_id)
        self.assertFalse(self.runner._tasks)
