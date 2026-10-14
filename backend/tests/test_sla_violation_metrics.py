# backend/tests/test_sla_violation_metrics.py
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import unittest

from src.application.services.sla_violation_metrics import build_sla_violation_report, sla_violation_window
from src.domain.constants import KST
from src.domain.entities.sla_violation_report import SlaViolationChange, SlaViolationCycle, SlaViolationIssue


def timestamp(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=KST)


def issue(**changes) -> SlaViolationIssue:
    base = SlaViolationIssue(
        key="TACEA-1234", summary="[서울교통공사] 개선의 건", created_at=timestamp(5),
        current_status="결과 대기 중", customer="서울교통공사", partners=(),
        reporter="김영준 과장", assignee="조장희 수석", tac_assignee="한준희 선임",
        cycles=(SlaViolationCycle("initial_response", timestamp(5, 12)), SlaViolationCycle("resolution", timestamp(7, 12))),
        changes=(SlaViolationChange(timestamp(6), "할 일", "연구소 검토 중"), SlaViolationChange(timestamp(8), "연구소 검토 중", "결과 대기 중")),
    )
    return replace(base, **changes)


class SlaViolationMetricsTest(unittest.TestCase):
    def build(self, issues=None, period="week", selected=date(2026, 10, 7), now=None):
        return build_sla_violation_report(tuple(issues if issues is not None else [issue()]), period, selected, now or timestamp(14), "tester")

    def test_periods_handle_monday_sunday_leap_month_and_year_boundary(self):
        for period, selected, expected_start, expected_end in (
            ("week", date(2026, 10, 11), date(2026, 10, 5), date(2026, 10, 12)),
            ("week", date(2026, 1, 1), date(2025, 12, 29), date(2026, 1, 5)),
            ("month", date(2024, 2, 29), date(2024, 2, 1), date(2024, 3, 1)),
            ("month", date(2025, 12, 31), date(2025, 12, 1), date(2026, 1, 1)),
            ("year", date(2024, 2, 29), date(2024, 1, 1), date(2025, 1, 1)),
        ):
            with self.subTest(period=period, selected=selected):
                start, end = sla_violation_window(period, selected)
                self.assertEqual((expected_start, expected_end), (start.date(), end.date()))
                self.assertEqual(timedelta(hours=9), start.utcoffset())

    def test_inclusion_uses_creation_in_kst_not_breach_date(self):
        start, end = sla_violation_window("week", date(2026, 10, 7))
        report = self.build([
            issue(key="IN", created_at=start.astimezone(timezone.utc), cycles=(SlaViolationCycle("resolution", timestamp(13)),)),
            issue(key="BEFORE", created_at=start - timedelta(seconds=1)),
            issue(key="AFTER", created_at=end),
            issue(key="CLEAN", cycles=()),
        ])
        self.assertEqual(["IN"], [row.key for row in report.tickets])
        self.assertEqual((date(2026, 10, 5), date(2026, 10, 11)), (report.start_date, report.end_date))

    def test_two_metrics_keep_separate_unique_counts_and_breach_status(self):
        report = self.build([issue(cycles=(*issue().cycles, SlaViolationCycle("resolution", timestamp(8, 12))))])
        self.assertEqual((1, 1, 1), (report.ticket_count, report.initial_response_count, report.resolution_count))
        row = report.tickets[0]
        self.assertEqual(["할 일", "연구소 검토 중", "결과 대기 중"], [breach.status for breach in row.breaches])
        self.assertEqual({"할 일": 24, "연구소 검토 중": 48, "결과 대기 중": 144}, {part.status: part.hours for part in row.status_durations})
        self.assertEqual(9, row.elapsed_days)

    def test_transition_boundary_uses_new_status_and_reentry_is_summed(self):
        sample = issue(current_status="할 일", changes=(SlaViolationChange(timestamp(6), "할 일", "검토 중"), SlaViolationChange(timestamp(7), "검토 중", "할 일")), cycles=(SlaViolationCycle("initial_response", timestamp(6)),))
        row = self.build([sample], now=timestamp(8)).tickets[0]
        self.assertEqual("검토 중", row.breaches[0].status)
        self.assertEqual({"할 일": 48, "검토 중": 24}, {part.status: part.hours for part in row.status_durations})

    def test_incomplete_history_retains_violation_but_never_invents_status_or_duration(self):
        for sample in (
            issue(history_complete=False),
            issue(current_status="다른 상태"),
            issue(changes=(SlaViolationChange(timestamp(6), "할 일", "검토 중"), SlaViolationChange(timestamp(8), "누락 상태", "결과 대기 중"))),
            issue(changes=(SlaViolationChange(timestamp(4), "할 일", "결과 대기 중"),)),
        ):
            row = self.build([sample]).tickets[0]
            self.assertIsNone(row.status_durations)
            self.assertTrue(all(breach.status is None for breach in row.breaches))
            self.assertTrue(row.warnings)

    def test_missing_breach_timestamp_is_not_derived_from_elapsed_time(self):
        row = self.build([issue(cycles=(SlaViolationCycle("resolution", None),))]).tickets[0]
        self.assertIsNone(row.breaches[0].breached_at)
        self.assertIsNone(row.breaches[0].status)
        self.assertIsNotNone(row.status_durations)
        self.assertTrue(row.warnings)

    def test_out_of_range_breach_has_unknown_status(self):
        row = self.build([issue(cycles=(SlaViolationCycle("resolution", timestamp(4)), SlaViolationCycle("resolution", timestamp(15))))]).tickets[0]
        self.assertTrue(all(breach.status is None for breach in row.breaches))
        self.assertTrue(row.warnings)

    def test_known_unassigned_partner_and_unknown_partner_remain_distinct(self):
        report = self.build([issue(key="HQ", partners=()), issue(key="UNKNOWN", partners=None)])
        values = {row.key: row.partners for row in report.tickets}
        self.assertEqual((), values["HQ"])
        self.assertIsNone(values["UNKNOWN"])

    def test_no_history_and_same_day_have_valid_zero_day_age(self):
        sample = issue(created_at=timestamp(7, 12), current_status="할 일", changes=(), cycles=(SlaViolationCycle("resolution", timestamp(7, 13)),))
        row = self.build([sample], now=timestamp(7, 14)).tickets[0]
        self.assertEqual(0, row.elapsed_days)
        self.assertEqual(2, row.status_durations[0].hours)

    def test_future_date_invalid_period_and_duplicate_ticket_are_rejected(self):
        with self.assertRaises(ValueError):
            self.build(selected=date(2026, 10, 15))
        with self.assertRaises(ValueError):
            self.build(period="quarter")
        with self.assertRaises(ValueError):
            self.build([issue(), issue()])

    def test_empty_report_is_valid_and_snapshot_age_is_fixed(self):
        report = self.build([])
        self.assertEqual((0, 0, 0, ()), (report.ticket_count, report.initial_response_count, report.resolution_count, report.tickets))
        earlier = self.build(now=timestamp(8))
        later = self.build(now=timestamp(14))
        self.assertEqual((3, 9), (earlier.tickets[0].elapsed_days, later.tickets[0].elapsed_days))
