# backend/tests/test_trigger_report_use_case.py
import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock

from src.application.errors import JobAlreadyRunningError
from src.application.ports.job_runner_port import JobRunnerPort
from src.application.use_cases.trigger_report import LatestReportUnavailableError, TriggerReportUseCase
from src.domain.constants import KST
from src.domain.entities.report import Report


class TriggerReportUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.runner = AsyncMock(spec=JobRunnerPort)
        self.reports = Mock(get_latest=AsyncMock(return_value=Report(
            id=17, week_start=date(2024, 2, 1), week_end=date(2024, 2, 29), report_date="2026-10-21",
        )))
        self.report_context_open = False
        self.report_context_entries = 0

        @asynccontextmanager
        async def get_report():
            self.report_context_open = True
            self.report_context_entries += 1
            try:
                yield self.reports
            finally:
                self.report_context_open = False

        self.clock = Mock(return_value=datetime(2026, 10, 13, 16, tzinfo=timezone.utc))
        self.use_case = TriggerReportUseCase(self.runner, get_report, self.clock)

    async def test_calendar_selection_uses_kst_and_needs_no_database_context(self) -> None:
        result = await self.use_case.execute(period="week", selected_date=date(2026, 10, 14))
        self.assertEqual(datetime(2026, 10, 12, tzinfo=KST), result.start_date)
        self.assertEqual(datetime(2026, 10, 18, 23, 59, 59, tzinfo=KST), result.end_date)
        self.assertEqual(0, self.report_context_entries)
        self.runner.submit.assert_awaited_once_with(
            result.job_id, result.start_date, result.end_date, bypass_jira_cache=True, force_standard=True,
        )

    async def test_rerun_releases_report_context_before_job_submission(self) -> None:
        async def submit(*args, **kwargs):
            self.assertFalse(self.report_context_open)

        self.runner.submit.side_effect = submit
        result = await self.use_case.execute(rerun_latest=True)
        self.assertEqual(1, self.report_context_entries)
        self.assertEqual(datetime(2024, 2, 1, tzinfo=KST), result.start_date)
        self.assertEqual(datetime(2024, 2, 29, 23, 59, 59, tzinfo=KST), result.end_date)
        self.clock.assert_not_called()
        self.runner.submit.assert_awaited_once_with(
            result.job_id, result.start_date, result.end_date, bypass_jira_cache=True, force_standard=True,
        )

    async def test_missing_report_releases_context_and_does_not_start_job(self) -> None:
        self.reports.get_latest.return_value = None
        with self.assertRaises(LatestReportUnavailableError):
            await self.use_case.execute(rerun_latest=True)
        self.assertFalse(self.report_context_open)
        self.runner.submit.assert_not_awaited()

    async def test_report_read_failure_releases_context_without_starting_job(self) -> None:
        self.reports.get_latest.side_effect = RuntimeError("unavailable")
        with self.assertRaises(RuntimeError):
            await self.use_case.execute(rerun_latest=True)
        self.assertFalse(self.report_context_open)
        self.runner.submit.assert_not_awaited()

    async def test_direct_call_rejects_conflicting_incomplete_or_invalid_selection(self) -> None:
        for values in (
            {"rerun_latest": True, "start_date": ""},
            {"period": "week"},
            {"selected_date": date(2026, 10, 14)},
            {"period": "month", "selected_date": date(2026, 10, 14), "end_date": "2026-10-31"},
            {"period": "year", "selected_date": date(2026, 10, 15)},
            {"start_date": "2026-02-30"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                await self.use_case.execute(**values)
        self.runner.submit.assert_not_awaited()
        self.assertEqual(0, self.report_context_entries)

    async def test_empty_and_legacy_date_requests_preserve_scope_selection(self) -> None:
        for values, dates in (
            ({}, (None, None)),
            ({"start_date": "", "end_date": ""}, (None, None)),
            ({"end_date": "2025-12-31"}, (None, datetime(2025, 12, 31, 23, 59, 59, tzinfo=KST))),
            ({"start_date": "2025-01-01"}, (datetime(2025, 1, 1, tzinfo=KST), None)),
        ):
            with self.subTest(values=values):
                result = await self.use_case.execute(**values)
                self.assertEqual(dates, (result.start_date, result.end_date))
                self.runner.submit.assert_awaited_with(result.job_id, *dates, bypass_jira_cache=True)
        self.assertEqual(0, self.report_context_entries)
        self.clock.assert_not_called()

    async def test_job_conflict_propagates_without_retrying_submission(self) -> None:
        self.runner.submit.side_effect = JobAlreadyRunningError("active-job")
        with self.assertRaises(JobAlreadyRunningError) as raised:
            await self.use_case.execute()
        self.assertEqual("active-job", raised.exception.job_id)
        self.assertEqual(1, self.runner.submit.await_count)
