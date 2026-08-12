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

        async def generate(
            start: datetime.datetime | None,
            end: datetime.datetime | None,
        ) -> Report:
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
