# backend/tests/test_c_level_core.py
from dataclasses import replace
from datetime import date, datetime
import json
import unittest

from src.application.ports.c_level_port import CLevelSourcePort
from src.application.services.c_level_metrics import issue_details, summarize_processing, summarize_sla
from src.application.services.c_level_periods import CLevelWindow, age_bucket, report_windows
from src.application.services.c_level_timeline import interval_at, reconstruct_history
from src.application.use_cases.c_level_report import CLevelReportUseCase
from src.domain.constants import KST
from src.domain.entities.c_level_report import CLevelIssue, CLevelSlaCycle, CLevelStatus, CLevelStatusChange


TODO = CLevelStatus("1", "할 일", "new")
REVIEW = CLevelStatus("2", "이슈 리뷰 중", "indeterminate")
REQUEST = CLevelStatus("3", "자료 요청 중", "indeterminate")
DONE = CLevelStatus("4", "Closed", "done")
REOPEN = CLevelStatus("5", "재오픈", "indeterminate")


def at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=KST) if parsed.tzinfo is None else parsed.astimezone(KST)


def change(timestamp: str, old: CLevelStatus, new: CLevelStatus) -> CLevelStatusChange:
    return CLevelStatusChange(at(timestamp), old, new)


def issue(key: str = "T-1", created: str = "2026-10-01", status: CLevelStatus = TODO, **values) -> CLevelIssue:
    return CLevelIssue(key, "테스트", "서비스 요청", at(created), status, **values)


class PeriodPolicyTest(unittest.TestCase):
    def test_week_has_seven_dates_and_exclusive_upper_bound(self):
        window, previous, trend = report_windows("week", date(2026, 10, 12), at("2026-10-13T09:00"))
        self.assertEqual(("2026-10-06", "2026-10-12"), (window.start_date, window.end_date))
        self.assertEqual(at("2026-10-13"), window.end)
        self.assertEqual(("2026-09-29", "2026-10-05"), (previous.start_date, previous.end_date))
        self.assertEqual(8, len(trend))
        self.assertEqual(at("2026-08-18"), trend[0].start)
        self.assertTrue(all(trend[index].end == trend[index + 1].start for index in range(7)))

    def test_current_month_is_mtd_and_comparison_uses_equal_calendar_point(self):
        window, previous, trend = report_windows("month", date(2026, 10, 1), at("2026-10-13T10:30"))
        self.assertEqual(at("2026-10-13T10:30"), window.end)
        self.assertEqual(at("2026-09-13T10:30"), previous.end)
        self.assertEqual(("2026-10-01", "2026-10-13"), (window.start_date, window.end_date))
        self.assertEqual(8, len(trend))
        self.assertEqual("2026-03-01", trend[0].start_date)

    def test_historical_month_is_complete_and_year_boundary_works(self):
        window, previous, _ = report_windows("month", date(2026, 1, 4), at("2026-10-13"))
        self.assertEqual(("2026-01-01", "2026-01-31"), (window.start_date, window.end_date))
        self.assertEqual(("2025-12-01", "2025-12-31"), (previous.start_date, previous.end_date))

    def test_calendar_month_buckets_clamp_anniversary_and_do_not_count_exclusive_next_day(self):
        self.assertEqual("1-3", age_bucket(at("2026-01-31T18:00"), at("2026-03-01")))
        self.assertIsNone(age_bucket(at("2026-01-31"), at("2026-02-28")))
        self.assertEqual("12+", age_bucket(at("2024-02-29"), at("2025-03-01")))
        self.assertEqual("3-6", age_bucket(at("2026-07-13"), at("2026-10-13T10:00")))
        self.assertEqual("1-3", age_bucket(at("2026-07-13"), at("2026-10-13")))

    def test_invalid_period_and_future_date_fail_before_source_access(self):
        for period, selected in (("year", date(2026, 1, 1)), ("week", date(2026, 10, 14))):
            with self.assertRaises(ValueError):
                report_windows(period, selected, at("2026-10-13T12:00"))

    def test_empty_current_month_at_midnight_has_valid_display_dates(self):
        window, _, _ = report_windows("month", None, at("2026-10-01"))
        self.assertEqual(("2026-10-01", "2026-10-01"), (window.start_date, window.end_date))


class HistoryPolicyTest(unittest.TestCase):
    def test_future_reopen_does_not_change_historical_done_state(self):
        item = issue(status=REOPEN, status_changes=(
            change("2026-10-10T10:00", TODO, DONE),
            change("2026-10-14T11:00", DONE, REOPEN),
        ))
        historical = reconstruct_history(item, at("2026-10-13"))
        self.assertEqual(DONE, historical.status)
        self.assertEqual(0, historical.reopen_count)
        current = reconstruct_history(item, at("2026-10-15"))
        self.assertEqual(REOPEN, current.status)
        self.assertEqual(1, current.reopen_count)

    def test_repeated_statuses_remain_distinct_intervals_and_deadline_uses_new_state(self):
        item = issue(status=REVIEW, status_changes=(
            change("2026-10-02", TODO, REVIEW),
            change("2026-10-03", REVIEW, REQUEST),
            change("2026-10-04", REQUEST, REVIEW),
        ))
        history = reconstruct_history(item, at("2026-10-05"))
        self.assertEqual([TODO, REVIEW, REQUEST, REVIEW], [part.status for part in history.intervals])
        self.assertEqual(REQUEST, interval_at(history, at("2026-10-03")).status)
        detail = issue_details(item, at("2026-10-05"), at("2026-10-10"))
        self.assertEqual(72, detail["owner_hours"]["TAC"])
        self.assertEqual(24, detail["owner_hours"]["고객·파트너"])

    def test_incomplete_history_cannot_become_current_state_at_past_cutoff(self):
        item = issue(status=DONE, history_complete=False)
        history = reconstruct_history(item, at("2026-10-13"))
        self.assertFalse(history.complete)
        self.assertIsNone(history.status)
        summary = summarize_processing((item,), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertEqual(0, summary["created"])
        self.assertIsNone(summary["resolved"])
        self.assertIsNone(summary["unresolved"])
        detail = issue_details(item, at("2026-10-13"), at("2026-10-20"))
        self.assertTrue(all(value is None for value in detail["owner_hours"].values()))

    def test_broken_transition_sequence_and_unknown_category_are_reported(self):
        for item in (
            issue(status_changes=(change("2026-10-02", TODO, REVIEW), change("2026-10-03", REQUEST, DONE))),
            issue(status=CLevelStatus("99", "삭제된 상태", "")),
        ):
            history = reconstruct_history(item, at("2026-10-13"))
            self.assertTrue(history.warnings)
            self.assertTrue(not history.complete or not history.status.category)

    def test_legacy_unknown_category_outside_window_preserves_known_current_metrics(self):
        legacy = CLevelStatus("99", "과거 상태", "")
        item = issue(created="2020-01-01", status=REVIEW, status_changes=(
            change("2020-02-01", legacy, TODO), change("2026-10-08", TODO, REVIEW),
        ))
        history = reconstruct_history(item, at("2026-10-13"))
        self.assertTrue(history.complete)
        self.assertEqual(REVIEW, history.status)
        self.assertIsNone(history.reopen_count)
        summary = summarize_processing((item,), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertEqual((0, 1), (summary["resolved"], summary["unresolved"]))

    def test_unknown_category_transition_in_window_does_not_hide_known_current_state(self):
        legacy = CLevelStatus("99", "과거 상태", "")
        item = issue(status=DONE, status_changes=(change("2026-10-08", legacy, DONE),))
        summary = summarize_processing((item,), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertIsNone(summary["resolved"])
        self.assertEqual(0, summary["unresolved"])

    def test_done_to_done_is_not_reopen_or_second_resolution(self):
        other_done = CLevelStatus("6", "취소됨", "done")
        item = issue(status=other_done, status_changes=(change("2026-10-02", TODO, DONE), change("2026-10-03", DONE, other_done)))
        history = reconstruct_history(item, at("2026-10-04"))
        self.assertEqual((at("2026-10-02"),), history.done_entries)
        self.assertEqual(0, history.reopen_count)


class ProcessingPolicyTest(unittest.TestCase):
    def test_done_events_count_unique_and_average_uses_last_done(self):
        item = issue(created="2026-10-06", status=DONE, status_changes=(
            change("2026-10-07", TODO, DONE), change("2026-10-08", DONE, REOPEN), change("2026-10-10", REOPEN, DONE),
        ))
        summary = summarize_processing((item,), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertEqual((1, 1, 0, 100.0, 4.0), tuple(summary[field] for field in ("created", "resolved", "unresolved", "resolution_rate", "average_resolution_days")))

    def test_old_backlog_resolution_does_not_inflate_created_cohort_rate(self):
        old = issue("T-1", status=DONE, status_changes=(change("2026-10-10", TODO, DONE),))
        new = issue("T-2", created="2026-10-08", status=REQUEST)
        summary = summarize_processing((old, new), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertEqual((1, 1, 1, 0.0), tuple(summary[field] for field in ("created", "resolved", "unresolved", "resolution_rate")))

    def test_cutoff_transition_and_creation_are_excluded(self):
        old = issue(status=DONE, status_changes=(change("2026-10-13", TODO, DONE),))
        future = issue("T-2", created="2026-10-13")
        summary = summarize_processing((old, future), CLevelWindow(at("2026-10-06"), at("2026-10-13")))[0]
        self.assertEqual((0, 0, 1), tuple(summary[field] for field in ("created", "resolved", "unresolved")))


class SlaPolicyTest(unittest.TestCase):
    def setUp(self):
        self.window = CLevelWindow(at("2026-10-06"), at("2026-10-13"))

    def aggregate(self, item, now="2026-10-20"):
        detail = issue_details(item, self.window.end, at(now))
        return summarize_sla((item,), [detail], self.window, at(now))

    def test_null_sla_and_no_cycles_are_not_successes(self):
        item = issue(sla_cycles=(CLevelSlaCycle("resolution", "unknown"),))
        sla, violations, _ = self.aggregate(item)
        stats = sla["by_type"][0]["resolution"]
        self.assertIsNone(stats["evaluated"])
        self.assertIsNone(stats["violations"])
        self.assertIsNone(stats["compliance_rate"])
        self.assertEqual(1, sla["coverage"]["unknown_cycles"])
        self.assertEqual([], violations)
        without, _, _ = self.aggregate(issue())
        self.assertEqual(1, without["coverage"]["issues_without_sla"])
        self.assertIsNone(without["violation_ticket_count"])
        self.assertIsNone(without["violation_event_count"])

    def test_completed_and_breached_ongoing_are_denominator_but_pending_is_not(self):
        item = issue(sla_cycles=(
            CLevelSlaCycle("resolution", "met", stop_at=at("2026-10-08"), breached=False),
            CLevelSlaCycle("resolution", "failed", breach_at=at("2026-10-09"), breached=True, ongoing=True),
            CLevelSlaCycle("resolution", "pending", breached=False, ongoing=True),
        ))
        sla, violations, _ = self.aggregate(item)
        stats = sla["by_type"][0]["resolution"]
        self.assertEqual((1, 2, 1, 50.0), tuple(stats[field] for field in ("violations", "evaluated", "met", "compliance_rate")))
        self.assertEqual(1, len(violations))
        self.assertIsNone(violations[0]["elapsed_hours"])
        self.assertIsNone(violations[0]["excess_hours"])

    def test_past_breach_completed_in_period_affects_rate_not_new_violation_count(self):
        item = issue(sla_cycles=(CLevelSlaCycle("resolution", "old", stop_at=at("2026-10-09"), breach_at=at("2026-10-03"), breached=True),))
        sla, violations, _ = self.aggregate(item)
        stats = sla["by_type"][0]["resolution"]
        self.assertEqual((0, 1, 0, 0.0), tuple(stats[field] for field in ("violations", "evaluated", "met", "compliance_rate")))
        self.assertEqual([], violations)

    def test_future_completed_cycle_is_ongoing_at_historical_cutoff(self):
        item = issue(sla_cycles=(CLevelSlaCycle("resolution", "later", start_at=at("2026-10-02"), stop_at=at("2026-10-15"), breach_at=at("2026-10-09"), elapsed_ms=300_000_000, breached=True),))
        sla, violations, _ = self.aggregate(item)
        self.assertEqual(1, sla["by_type"][0]["resolution"]["evaluated"])
        self.assertTrue(violations[0]["is_ongoing"])
        detail = issue_details(item, self.window.end, at("2026-10-20"))
        self.assertIsNone(detail["sla_cycles"][0]["elapsed_hours"])
        self.assertIsNone(detail["sla_cycles"][0]["stop_at"])

    def test_sla_uses_engine_milliseconds_not_wall_time_and_deduplicates_cycles(self):
        cycle = CLevelSlaCycle("resolution", "cycle", start_at=at("2026-10-01"), stop_at=at("2026-10-10"), breach_at=at("2026-10-09"), goal_ms=3_600_000, elapsed_ms=5_400_000, remaining_ms=-1_800_000, breached=True)
        item = issue(sla_cycles=(cycle, cycle))
        sla, violations, _ = self.aggregate(item)
        self.assertEqual(1, sla["violation_ticket_count"])
        self.assertEqual(1, sla["violation_event_count"])
        self.assertEqual((1.0, 1.5, 0.5), tuple(violations[0][field] for field in ("goal_hours", "elapsed_hours", "excess_hours")))

    def test_both_metrics_count_two_events_for_one_ticket(self):
        item = issue(sla_cycles=tuple(CLevelSlaCycle(metric, metric, breach_at=at("2026-10-09"), breached=True, ongoing=True) for metric in ("initial_response", "resolution")))
        sla, _, _ = self.aggregate(item)
        self.assertEqual((1, 2), (sla["violation_ticket_count"], sla["violation_event_count"]))

    def test_missing_deadline_is_reported_and_future_deadline_not_in_period(self):
        item = issue(sla_cycles=(CLevelSlaCycle("resolution", "missing", breached=True), CLevelSlaCycle("resolution", "future", breached=True, breach_at=at("2026-10-13"))))
        sla, violations, warnings = self.aggregate(item)
        self.assertEqual([], violations)
        self.assertEqual(0, sla["by_type"][0]["resolution"]["evaluated"])
        self.assertTrue(warnings)

    def test_sla_first_response_precedes_auxiliary_field_and_reopen_gap_warns(self):
        item = issue(status=REOPEN, status_changes=(change("2026-10-08", TODO, DONE), change("2026-10-10", DONE, REOPEN)), first_response_at=at("2026-10-02T09:09:21"), sla_cycles=(CLevelSlaCycle("initial_response", "first", stop_at=at("2026-10-02T09:09:31"), breached=False),))
        detail = issue_details(item, self.window.end, at("2026-10-20"))
        self.assertEqual(at("2026-10-02T09:09:31").isoformat(), detail["first_response_at"])
        self.assertEqual("sla_cycle", detail["first_response_source"])
        self.assertTrue(any("재오픈 이후" in warning for warning in detail["warnings"]))


class ReportUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_long_term_comparison_reconstructs_previous_state_and_calendar_boundary_once(self):
        values = (
            issue("T-1", created="2025-10-10"),
            issue("T-2", created="2025-01-01", status=DONE, status_changes=(change("2026-10-08", TODO, DONE),)),
            issue("T-3", created="2026-09-10"),
        )

        class Source(CLevelSourcePort):
            calls = 0

            async def fetch_issues(self, earliest, as_of, refresh=False):
                self.calls += 1
                return values

        source = Source()
        result = await CLevelReportUseCase(source).execute("week", date(2026, 10, 12), now=at("2026-10-13"))
        long_term = result["long_term"]
        self.assertEqual(1, source.calls)
        self.assertEqual(2, long_term["previous_total"])
        self.assertEqual(0, long_term["delta_total"])
        self.assertEqual(1, long_term["previous_over_12_months"])
        self.assertEqual(0, long_term["delta_over_12_months"])

    async def test_long_term_comparison_preserves_unknown_previous_status(self):
        legacy = CLevelStatus("99", "과거 상태", "")

        class Source(CLevelSourcePort):
            async def fetch_issues(self, earliest, as_of, refresh=False):
                return (issue(created="2025-01-01", status=TODO, status_changes=(change("2026-10-08", legacy, TODO),)),)

        result = await CLevelReportUseCase(Source()).execute("week", date(2026, 10, 12), now=at("2026-10-13"))
        long_term = result["long_term"]
        self.assertEqual(1, long_term["buckets"][3]["count"])
        self.assertIsNone(long_term["previous_total"])
        self.assertIsNone(long_term["delta_total"])
        self.assertIsNone(long_term["previous_over_12_months"])
        self.assertIsNone(long_term["delta_over_12_months"])

    async def test_report_filters_types_groups_calendar_ages_and_is_json_snapshot_ready(self):
        values = (
            issue("T-1", created="2026-01-31", customer_name="고객 A", partner_names=("파트너",), tac_assignee="담당"),
            issue("T-2", created="2026-02-01", customer_name=" 고객  A "),
            issue("T-3", created="2025-01-01"),
            replace(issue("T-4"), issue_type="라이선스"),
        )

        class Source(CLevelSourcePort):
            async def fetch_issues(self, earliest, as_of, refresh=False):
                self.request = (earliest, as_of, refresh)
                return values

        source = Source()
        result = await CLevelReportUseCase(source).execute("month", date(2026, 2, 1), True, at("2026-10-13"))
        self.assertEqual(3, len(result["issues"]))
        self.assertEqual(8, len(result["trend"]))
        self.assertEqual("2026-02-28", result["end_date"])
        self.assertTrue(source.request[2])
        first = result["long_term"]["buckets"][0]
        self.assertEqual((1, 1), (first["count"], first["customer_count"]))
        self.assertEqual(1, result["long_term"]["unassigned_customer_issue_count"])
        self.assertEqual(3, len(result["source_issues"]))
        self.assertIn("policy_version", json.loads(json.dumps(result, ensure_ascii=False)))
        self.assertEqual(0, result["long_term"]["buckets"][3]["customer_count"])

    async def test_current_status_without_resolution_timestamp_is_unresolved(self):
        class Source(CLevelSourcePort):
            async def fetch_issues(self, earliest, as_of, refresh=False):
                return (issue(status=REQUEST),)

        result = await CLevelReportUseCase(Source()).execute("week", date(2026, 10, 12), now=at("2026-10-13"))
        self.assertEqual(1, result["summary"][0]["unresolved"])
        self.assertEqual(0, result["summary"][0]["resolved"])
        self.assertIsNone(result["sla"]["violation_event_count"])
        self.assertIsNone(result["sla"]["by_type"][0]["initial_response"]["compliance_rate"])

    async def test_unknown_long_term_status_remains_null_in_bucket(self):
        class Source(CLevelSourcePort):
            async def fetch_issues(self, earliest, as_of, refresh=False):
                return (issue(created="2026-01-01", status=CLevelStatus("99", "삭제 상태", "")),)

        result = await CLevelReportUseCase(Source()).execute("week", date(2026, 10, 12), now=at("2026-10-13"))
        bucket = result["long_term"]["buckets"][2]
        self.assertIsNone(bucket["count"])
        self.assertIsNone(bucket["customer_count"])
        self.assertIsNone(bucket["by_type"]["service"])
        self.assertEqual(0, bucket["known_count"])
        self.assertEqual(1, bucket["unknown_status_count"])
        self.assertEqual("확인 불가", result["issues"][0]["customer_name"])
