# backend/tests/test_jira_sla_calendar.py
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
import unittest

import httpx

from src.application.services.sla_violation_metrics import build_sla_violation_report
from src.infrastructure.external.jira_sla_calendar import calendar_ids_for_project, parse_clock_calendar
from src.infrastructure.external.sla_violation_jira_source import SlaViolationJiraSource, _snapshot_window
from tests.test_sla_violation_jira_source import _KST, _START, _END, history, history_page, issue


def calendar_payload():
    return {
        "id": 1, "name": "Tech-Ops 9-6", "timezoneId": "Asia/Seoul",
        "workingTimes": [
            {"weekday": day, "start": start, "end": end}
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
            for start, end in ((32_400_000, 43_200_000), (46_800_000, 64_800_000))
        ],
        "holidays": [{"iso8601Date": "2026-05-05", "recurring": False}],
    }


class JiraSlaCalendarTest(unittest.TestCase):
    def test_http_date_uses_only_second_precision_and_measured_request_duration(self):
        before = datetime.fromisoformat("2026-10-16T14:04:24.776207+09:00")
        after = datetime.fromisoformat("2026-10-16T14:04:25.135354+09:00")
        lower, upper = _snapshot_window("Fri, 16 Oct 2026 05:04:26 GMT", before, after, timedelta(microseconds=359147))
        self.assertEqual(datetime.fromisoformat("2026-10-16T14:04:25.640853+09:00"), lower)
        self.assertEqual(datetime.fromisoformat("2026-10-16T14:04:27.359147+09:00"), upper)
        self.assertEqual(timezone.utc, lower.tzinfo)
        self.assertEqual(timedelta(seconds=1, microseconds=718294), upper - lower)

    def test_missing_or_invalid_http_date_falls_back_to_local_observation(self):
        before = datetime(2026, 10, 16, 14, tzinfo=_KST)
        after = before + timedelta(milliseconds=300)
        for header in (None, "", "not a date", "Fri, 16 Oct 2026 05:04:26", "Fri, 16 Oct 2026 05:04:26 +0000", "Fri, 16 Oct 2026 14:04:26 KST", "Fri, 16 Oct 2026 05:04:26 UTC", "Fri, 32 Oct 2026 05:04:26 GMT", "Fri, 16 Oct 2026 25:04:26 GMT", "Thu, 16 Oct 2026 05:04:26 GMT"):
            with self.subTest(header=header):
                self.assertEqual((before, after), _snapshot_window(header, before, after, timedelta(milliseconds=300)))

    def test_project_selection_includes_shared_desk_and_excludes_other_projects(self):
        self.assertEqual(("1", "3"), calendar_ids_for_project({"calendars": [
            {"id": 1, "context": {"serviceDeskId": "1"}},
            {"id": 3, "context": {"serviceDeskId": "1", "projectId": "10005"}},
            {"id": 9, "context": {"serviceDeskId": "9", "projectId": "999"}},
        ]}, "10005"))
        self.assertEqual((), calendar_ids_for_project({"calendars": []}, "10005"))

    def test_calendar_preserves_real_holidays_without_inventing_korean_holidays(self):
        calendar = parse_clock_calendar(calendar_payload(), "1")
        self.assertEqual("Asia/Seoul", calendar.timezone)
        self.assertEqual(10, len(calendar.working_times))
        self.assertEqual((date(2026, 5, 5),), tuple(holiday.day for holiday in calendar.holidays))
        self.assertNotIn(date(2026, 10, 9), tuple(holiday.day for holiday in calendar.holidays))

    def test_incomplete_or_invalid_calendar_is_never_assumed_to_be_24_7(self):
        for changes in (
            {"holidays": None}, {"workingTimes": None}, {"timezoneId": "Invalid/Zone"},
            {"workingTimes": [{"weekday": "monday", "start": True, "end": 1000}]},
            {"holidays": [{"iso8601Date": "2026-02-30", "recurring": False}]},
            {"id": 2},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_clock_calendar({**calendar_payload(), **changes}, "1")


class JiraSlaClockCollectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_http_date_reconciles_running_sla_when_local_clock_is_behind(self):
        local_before = datetime.fromisoformat("2026-10-16T14:04:24.776207+09:00")
        local_after = datetime.fromisoformat("2026-10-16T14:04:25.135354+09:00")
        candidate = issue(
            "TACEA-CLOCK", created="2026-10-16T14:00:00+09:00", status={"name": "이슈 리뷰 중"},
            project={"id": "10005"}, customfield_12152=None,
            customfield_12151={"ongoingCycle": {
                "breached": True, "paused": False,
                "startTime": {"jira": "2026-10-16T14:00:00+09:00"},
                "breachTime": {"jira": "2026-10-16T14:01:00+09:00"},
                "goalDuration": {"millis": 60_000}, "elapsedTime": {"millis": 266_500},
                "remainingTime": {"millis": -206_500},
            }},
        )

        def handler(request):
            if request.url.path.endswith("/search/jql"):
                return httpx.Response(200, headers={"Date": "Fri, 16 Oct 2026 05:04:26 GMT"}, json={"issues": [candidate], "isLast": True})
            if request.url.path.endswith("/calendar"):
                data = {"calendars": [{"id": 1, "context": {"serviceDeskId": "1", "projectId": "10005"}}]}
            elif request.url.path.endswith("/calendar/1"):
                data = calendar_payload()
            else:
                data = history_page()
            return httpx.Response(200, json=data)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch("src.infrastructure.external.sla_violation_jira_source.datetime") as clock, patch("src.infrastructure.external.sla_violation_jira_source.monotonic_ns", side_effect=(1_000_000_000, 1_359_147_000)):
                clock.now.side_effect = (local_before, local_after)
                clock.fromisoformat.side_effect = datetime.fromisoformat
                clock.fromtimestamp.side_effect = datetime.fromtimestamp
                async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                    issues = await source.fetch_issues(_START, _END)
        collected = issues[0]
        self.assertEqual(datetime.fromisoformat("2026-10-16T14:04:25.640853+09:00"), collected.clock_snapshot_before)
        self.assertEqual(datetime.fromisoformat("2026-10-16T14:04:27.359147+09:00"), collected.clock_snapshot_after)

        report = build_sla_violation_report(issues, "month", local_after.date(), local_after, "tester")
        self.assertEqual(local_after, report.generated_at)
        self.assertEqual(266_500, round(report.tickets[0].status_durations[0].hours * 3_600_000))
        self.assertEqual("이슈 리뷰 중", report.tickets[0].breaches[0].status)

        for elapsed in (264_000, 268_000):
            with self.subTest(outside_observation_elapsed=elapsed):
                mismatch = replace(collected, cycles=(replace(collected.cycles[0], elapsed_ms=elapsed),))
                ticket = build_sla_violation_report((mismatch,), "month", local_after.date(), local_after, "tester").tickets[0]
                self.assertIsNone(ticket.status_durations)
                self.assertIn("일치하지", " ".join(ticket.warnings))

        future_breach = replace(collected, cycles=(replace(collected.cycles[0], breached_at=datetime.fromisoformat("2026-10-16T14:04:26+09:00")),))
        ticket = build_sla_violation_report((future_breach,), "month", local_after.date(), local_after, "tester").tickets[0]
        self.assertIsNotNone(ticket.status_durations)
        self.assertIsNone(ticket.breaches[0].status)
        self.assertIn("집계 시점 범위를 벗어나", " ".join(ticket.warnings))

    async def test_search_uses_local_times_when_date_is_missing_and_measures_each_page_separately(self):
        moments = tuple(datetime(2026, 10, 16, 14, minute, tzinfo=_KST) for minute in range(4))
        responses = iter((
            httpx.Response(200, json={"issues": [issue("ONE")], "nextPageToken": "next", "isLast": False}),
            httpx.Response(200, headers={"Date": "Fri, 16 Oct 2026 05:04:26 GMT"}, json={"issues": [issue("TWO")], "isLast": True}),
        ))
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: next(responses))) as client:
            with patch("src.infrastructure.external.sla_violation_jira_source.datetime") as clock, patch("src.infrastructure.external.sla_violation_jira_source.monotonic_ns", side_effect=(0, 400_000_000, 1_000_000_000, 1_250_000_000)):
                clock.now.side_effect = moments
                async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                    rows = await source._search("project=TACEA")
        self.assertEqual((moments[0], moments[1]), (rows[0]["_sla_snapshot_before"], rows[0]["_sla_snapshot_after"]))
        self.assertEqual(datetime.fromisoformat("2026-10-16T05:04:25.750000+00:00"), rows[1]["_sla_snapshot_before"])
        self.assertEqual(datetime.fromisoformat("2026-10-16T05:04:27.250000+00:00"), rows[1]["_sla_snapshot_after"])

    async def test_collects_real_calendar_and_reconciles_ticket_clock(self):
        candidate = issue(
            "TACEA-4943", created="2026-10-08T11:05:57.359+09:00", project={"id": "10005"},
            customfield_12152=None,
            customfield_12151={"ongoingCycle": {
                "breached": True, "paused": True,
                "startTime": {"jira": "2026-10-08T11:05:57.359+09:00"},
                "breachTime": {"jira": "2026-10-15T11:05:57.359+09:00"},
                "goalDuration": {"millis": 144_000_000}, "elapsedTime": {"millis": 165_242_641},
                "remainingTime": {"millis": -21_242_641},
            }},
        )
        paths = []

        def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith("/search/jql"):
                data = {"issues": [candidate], "isLast": True}
            elif request.url.path.endswith("/calendar"):
                data = {"calendars": [{"id": 1, "context": {"serviceDeskId": "1", "projectId": "10005"}}]}
            elif request.url.path.endswith("/calendar/1"):
                data = calendar_payload()
            else:
                data = history_page([
                    history("1", "2026-10-08T12:43:56.722+09:00", "할 일", "이슈 리뷰 중"),
                    history("2", "2026-10-15T18:03:19.732+09:00", "이슈 리뷰 중", "결과 대기 중"),
                ], total=2)
            return httpx.Response(200, json=data)

        now = datetime(2026, 10, 16, 14, tzinfo=_KST)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch("src.infrastructure.external.sla_violation_jira_source.datetime") as clock:
                clock.now.return_value = now
                clock.fromisoformat.side_effect = datetime.fromisoformat
                clock.fromtimestamp.side_effect = datetime.fromtimestamp
                async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                    issues = await source.fetch_issues(_START, _END)
        report = build_sla_violation_report(issues, "month", now.date(), now, "tester")
        ticket = report.tickets[0]
        self.assertEqual("resolution_sla", ticket.status_durations_basis)
        self.assertEqual("Tech-Ops 9-6", ticket.status_duration_calendar)
        millis = {part.status: round(part.hours * 3_600_000) for part in ticket.status_durations}
        self.assertEqual({"할 일": 3_242_641, "이슈 리뷰 중": 162_000_000, "결과 대기 중": 0}, millis)
        self.assertEqual(165_242_641, sum(millis.values()))
        self.assertEqual(1, paths.count("/rest/workinghours/1/api/calendar"))

    async def test_missing_calendar_permission_is_unknown_but_network_failure_propagates(self):
        for status in (403, 404, 500):
            with self.subTest(status=status):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, json={}))) as client:
                    async with SlaViolationJiraSource("https://jira.example.com", "user", "token", client=client) as source:
                        if status == 500:
                            with self.assertRaises(RuntimeError):
                                await source._calendars("10005")
                        else:
                            self.assertEqual((), await source._calendars("10005"))
