# backend/tests/test_custom_report_period.py
import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from src.application.ports.job_runner_port import JobRunnerPort
from src.application.services.report_period import custom_report_dates, report_period_dates
from src.application.use_cases.trigger_report import TriggerReportUseCase
from src.domain.constants import KST
from src.domain.entities.report import Report
from src.presentation.api.deps import get_audit, get_trigger_report_use_case
from src.presentation.api.v1.trigger import router


class CustomReportDatesTest(unittest.TestCase):
    def test_exact_day_leap_day_and_cross_year_ranges_keep_inclusive_kst_boundaries(self):
        for start_text, end_text in (
            ("2026-10-29", "2026-10-29"),
            ("2024-02-28", "2024-02-29"),
            ("2024-02-29", "2024-02-29"),
            ("2025-12-30", "2026-01-02"),
        ):
            with self.subTest(start=start_text, end=end_text):
                start, end = custom_report_dates(start_text, end_text, date(2026, 10, 29))
                self.assertEqual(start_text, start.date().isoformat())
                self.assertEqual(end_text, end.date().isoformat())
                self.assertEqual((0, 0, 0, 0), (start.hour, start.minute, start.second, start.microsecond))
                self.assertEqual((23, 59, 59, 0), (end.hour, end.minute, end.second, end.microsecond))
                self.assertEqual(timedelta(hours=9), start.utcoffset())
                self.assertEqual(timedelta(hours=9), end.utcoffset())

    def test_both_bounds_require_strict_real_calendar_dates(self):
        for invalid in (
            "", "2026-1-01", "2026-01-1", "20260101", "2026/01/01",
            "2026-01-01T00:00:00", "2026-01-01Z", " 2026-01-01", "2026-01-01 ",
            "2025-02-29", "2026-02-30", "2026-13-01", "0000-01-01",
            "２０２６-０１-０１", None, 20260101,
        ):
            for start, end in ((invalid, "2026-10-29"), ("2024-01-01", invalid)):
                with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                    custom_report_dates(start, end, date(2026, 10, 29))

    def test_reversed_and_future_ranges_fail_but_today_is_inclusive(self):
        for start, end in (("2026-10-29", "2026-10-28"), ("2026-10-29", "2026-10-30")):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                custom_report_dates(start, end, date(2026, 10, 29))
        self.assertEqual(date(2026, 10, 29), custom_report_dates("2026-10-29", "2026-10-29", date(2026, 10, 29))[1].date())

    def test_existing_calendar_periods_still_keep_whole_periods(self):
        for period, expected in (
            ("day", (date(2026, 10, 29), date(2026, 10, 29))),
            ("week", (date(2026, 10, 26), date(2026, 11, 1))),
            ("month", (date(2026, 10, 1), date(2026, 10, 31))),
            ("year", (date(2026, 1, 1), date(2026, 12, 31))),
        ):
            with self.subTest(period=period):
                result = report_period_dates(period, date(2026, 10, 29), date(2026, 10, 29))
                self.assertEqual(expected, tuple(value.date() for value in result))


class CustomReportTriggerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runner = AsyncMock(spec=JobRunnerPort)
        self.reports = Mock(get_latest=AsyncMock())
        self.report_context_open = False
        self.report_context_entries = 0
        self.clock = Mock(return_value=datetime(2026, 10, 29, 12, tzinfo=KST))

        @asynccontextmanager
        async def get_report():
            self.report_context_entries += 1
            self.report_context_open = True
            try:
                yield self.reports
            finally:
                self.report_context_open = False

        self.use_case = TriggerReportUseCase(self.runner, get_report, self.clock)

    async def test_custom_request_submits_exact_range_fresh_and_standard_without_report_read(self):
        result = await self.use_case.execute(period="custom", start_date="2025-12-30", end_date="2026-01-02")
        self.runner.submit.assert_awaited_once_with(
            result.job_id, datetime(2025, 12, 30, tzinfo=KST),
            datetime(2026, 1, 2, 23, 59, 59, tzinfo=KST),
            bypass_jira_cache=True, force_standard=True,
        )
        self.assertEqual(0, self.report_context_entries)
        self.reports.get_latest.assert_not_awaited()

    async def test_full_year_custom_range_remains_standard_while_legacy_scope_is_unchanged(self):
        values = {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        custom = await self.use_case.execute(period="custom", **values)
        self.runner.submit.assert_awaited_with(
            custom.job_id, custom.start_date, custom.end_date, bypass_jira_cache=True, force_standard=True,
        )
        legacy = await self.use_case.execute(**values)
        self.assertEqual((custom.start_date, custom.end_date), (legacy.start_date, legacy.end_date))
        self.runner.submit.assert_awaited_with(
            legacy.job_id, legacy.start_date, legacy.end_date, bypass_jira_cache=True,
        )

    async def test_legacy_partial_dates_and_empty_requests_preserve_existing_submission(self):
        for values, expected in (
            ({}, (None, None)),
            ({"start_date": "", "end_date": ""}, (None, None)),
            ({"start_date": "2025-01-01"}, (datetime(2025, 1, 1, tzinfo=KST), None)),
            ({"end_date": "2025-12-31"}, (None, datetime(2025, 12, 31, 23, 59, 59, tzinfo=KST))),
        ):
            with self.subTest(values=values):
                result = await self.use_case.execute(**values)
                self.assertEqual(expected, (result.start_date, result.end_date))
                self.runner.submit.assert_awaited_with(result.job_id, *expected, bypass_jira_cache=True)
        self.clock.assert_not_called()

    async def test_direct_invalid_requests_do_not_submit_or_open_report_context(self):
        for values in (
            {}, {"start_date": "2026-10-01"}, {"end_date": "2026-10-29"},
            {"start_date": "", "end_date": "2026-10-29"},
            {"start_date": "2026-02-30", "end_date": "2026-10-29"},
            {"start_date": "2026-10-29", "end_date": "2026-10-28"},
            {"start_date": "2026-10-29", "end_date": "2026-10-30"},
            {"start_date": "2026-10-01", "end_date": "2026-10-29", "selected_date": date(2026, 10, 29)},
            {"start_date": "2026-10-01", "end_date": "2026-10-29", "rerun_latest": True},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                await self.use_case.execute(period="custom", **values)
        self.runner.submit.assert_not_awaited()
        self.reports.get_latest.assert_not_awaited()
        self.assertEqual(0, self.report_context_entries)

    async def test_kst_midnight_controls_future_validation_before_utc_midnight(self):
        self.clock.return_value = datetime(2026, 10, 28, 14, 59, 59, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            await self.use_case.execute(period="custom", start_date="2026-10-29", end_date="2026-10-29")
        self.runner.submit.assert_not_awaited()
        self.clock.return_value = datetime(2026, 10, 28, 15, 0, 0, tzinfo=timezone.utc)
        result = await self.use_case.execute(period="custom", start_date="2026-10-29", end_date="2026-10-29")
        self.assertEqual(datetime(2026, 10, 29, tzinfo=KST), result.start_date)
        self.assertEqual(datetime(2026, 10, 29, 23, 59, 59, tzinfo=KST), result.end_date)

    async def test_latest_saved_custom_range_reruns_exact_dates_without_current_date_validation(self):
        self.reports.get_latest.return_value = Report(
            id=35, week_start=date(2024, 2, 29), week_end=date(2025, 1, 3), report_date="2026-10-29",
        )

        async def submit(*args, **kwargs):
            self.assertFalse(self.report_context_open)

        self.runner.submit.side_effect = submit
        result = await self.use_case.execute(rerun_latest=True)
        self.reports.get_latest.assert_awaited_once_with(bypass_cache=True)
        self.clock.assert_not_called()
        self.runner.submit.assert_awaited_once_with(
            result.job_id, datetime(2024, 2, 29, tzinfo=KST),
            datetime(2025, 1, 3, 23, 59, 59, tzinfo=KST),
            bypass_jira_cache=True, force_standard=True,
        )


class CustomReportTriggerApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runner = AsyncMock(spec=JobRunnerPort)
        self.audit = Mock()
        self.reports = Mock(get_latest=AsyncMock())
        self.clock = Mock(return_value=datetime(2026, 10, 29, 12, tzinfo=KST))

        @asynccontextmanager
        async def get_report():
            yield self.reports

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        use_case = TriggerReportUseCase(self.runner, get_report, self.clock)
        app.dependency_overrides[get_trigger_report_use_case] = lambda: use_case
        app.dependency_overrides[get_audit] = lambda: self.audit
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_custom_http_request_submits_and_audits_same_inclusive_range(self):
        for start, end in (("2024-02-29", "2024-02-29"), ("2025-01-01", "2025-12-31"), ("2025-12-30", "2026-01-02")):
            with self.subTest(start=start, end=end):
                response = await self.client.post("/api/v1/trigger/", json={"period": "custom", "start_date": start, "end_date": end})
                self.assertEqual(202, response.status_code, response.text)
                args, kwargs = self.runner.submit.await_args
                self.assertEqual(response.json()["job_id"], args[0])
                self.assertEqual((start, end), (args[1].date().isoformat(), args[2].date().isoformat()))
                self.assertEqual({"bypass_jira_cache": True, "force_standard": True}, kwargs)
                self.assertEqual(start, self.audit.record.call_args.kwargs["start"])
                self.assertEqual(end, self.audit.record.call_args.kwargs["end"])

    async def test_invalid_http_ranges_and_conflicts_create_neither_jobs_nor_audits(self):
        valid = {"period": "custom", "start_date": "2026-10-01", "end_date": "2026-10-29"}
        invalid = [
            {"period": "custom"}, {"period": "custom", "start_date": "2026-10-01"},
            {"period": "custom", "end_date": "2026-10-29"},
            {**valid, "start_date": None}, {**valid, "end_date": None},
            {**valid, "date": "2026-10-29"}, {**valid, "rerun_latest": True},
            {**valid, "start_date": "2026-10-30"}, {**valid, "end_date": "2026-10-30"},
            {**valid, "period": "day", "date": "2026-10-29"},
            {**valid, "start_date": 20261001},
        ]
        for malformed in ("", "2026-2-01", "2026-02-30", "2025-02-29", "20261001", "2026-10-01T00:00:00", " 2026-10-01"):
            invalid.extend(({**valid, "start_date": malformed}, {**valid, "end_date": malformed}))
        for body in invalid:
            with self.subTest(body=body):
                response = await self.client.post("/api/v1/trigger/", json=body)
                self.assertEqual(422, response.status_code, response.text)
        self.runner.submit.assert_not_awaited()
        self.reports.get_latest.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_http_request_uses_kst_today_across_utc_day_boundary(self):
        payload = {"period": "custom", "start_date": "2026-10-29", "end_date": "2026-10-29"}
        self.clock.return_value = datetime(2026, 10, 28, 14, 59, 59, tzinfo=timezone.utc)
        response = await self.client.post("/api/v1/trigger/", json=payload)
        self.assertEqual(422, response.status_code, response.text)
        self.runner.submit.assert_not_awaited()
        self.audit.record.assert_not_called()
        self.clock.return_value = datetime(2026, 10, 28, 15, tzinfo=timezone.utc)
        response = await self.client.post("/api/v1/trigger/", json=payload)
        self.assertEqual(202, response.status_code, response.text)
        self.runner.submit.assert_awaited_once()
        self.audit.record.assert_called_once()

    async def test_http_latest_refresh_uses_saved_custom_dates(self):
        self.reports.get_latest.return_value = Report(
            id=35, week_start=date(2025, 12, 30), week_end=date(2026, 1, 2), report_date="2026-10-29",
        )
        response = await self.client.post("/api/v1/trigger/", json={"rerun_latest": True})
        self.assertEqual(202, response.status_code, response.text)
        self.runner.submit.assert_awaited_once_with(
            response.json()["job_id"], datetime(2025, 12, 30, tzinfo=KST),
            datetime(2026, 1, 2, 23, 59, 59, tzinfo=KST), bypass_jira_cache=True, force_standard=True,
        )
        self.reports.get_latest.assert_awaited_once_with(bypass_cache=True)
        self.clock.assert_not_called()
