# backend/tests/test_sla_status_clock.py
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import unittest

from src.application.services.sla_status_clock import calculate_sla_status_durations
from src.domain.constants import KST
from src.domain.entities.sla_clock import SlaClockCalendar, SlaClockHoliday, SlaClockWorkingTime
from src.domain.entities.sla_violation_report import SlaViolationCycle


HOUR = 3_600_000


def timestamp(day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=KST)


def business_calendar(**changes) -> SlaClockCalendar:
    calendar = SlaClockCalendar(
        id="1", name="Tech-Ops 9-6", timezone="Asia/Seoul",
        working_times=tuple(SlaClockWorkingTime(weekday, start * HOUR, end * HOUR) for weekday in range(5) for start, end in ((9, 12), (13, 18))),
    )
    return replace(calendar, **changes)


def completed(start: datetime, end: datetime, hours: float) -> SlaViolationCycle:
    return SlaViolationCycle("resolution", None, elapsed_ms=round(hours * HOUR), started_at=start, stopped_at=end)


class SlaStatusClockTest(unittest.TestCase):
    def calculate(self, intervals, cycles, calendars=None, before=None, after=None):
        return calculate_sla_status_durations(tuple(intervals), tuple(cycles), tuple(calendars or (business_calendar(),)), before, after)

    def values(self, result):
        self.assertIsNotNone(result.durations, result.warning)
        return {duration.status: duration.hours for duration in result.durations}

    def test_tacea_4943_matches_real_jira_milliseconds_and_does_not_assume_hangul_holiday(self):
        created = datetime.fromisoformat("2026-10-08T11:05:57.359+09:00")
        reviewed = datetime.fromisoformat("2026-10-08T12:43:56.722+09:00")
        waiting = datetime.fromisoformat("2026-10-15T18:03:19.732+09:00")
        before, after = timestamp(16, 11), timestamp(16, 11, 1)
        intervals = ((created, reviewed, "할 일"), (reviewed, waiting, "이슈 리뷰 중"), (waiting, after, "결과 대기 중"))
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=True, elapsed_ms=165_242_641, started_at=created)
        result = self.calculate(intervals, (cycle,), before=before, after=after)
        durations = self.values(result)
        self.assertEqual(3_242_641, round(durations["할 일"] * HOUR))
        self.assertEqual(45, durations["이슈 리뷰 중"])
        self.assertEqual(0, durations["결과 대기 중"])
        self.assertEqual(165_242_641, round(sum(durations.values()) * HOUR))
        self.assertEqual(("Tech-Ops 9-6",), result.calendar_names)
        mismatched = self.calculate(intervals, (cycle,), (business_calendar(holidays=(SlaClockHoliday(date(2026, 10, 9)),)),), before, after)
        self.assertIsNone(mismatched.durations)
        self.assertIn("일치하지", mismatched.warning)

    def test_configured_holiday_weekend_lunch_and_pause_are_excluded(self):
        intervals = ((timestamp(8, 9), timestamp(8, 11), "할 일"), (timestamp(8, 11), timestamp(12, 16), "검토 중"), (timestamp(12, 16), timestamp(13), "결과대기중"))
        cycle = completed(timestamp(8, 9), timestamp(13), 14)
        result = self.calculate(intervals, (cycle,), (business_calendar(holidays=(SlaClockHoliday(date(2026, 10, 9)),)),))
        self.assertEqual({"할 일": 2, "검토 중": 12, "결과대기중": 0}, self.values(result))

    def test_recurring_holiday_applies_across_years_and_one_time_holiday_does_not(self):
        intervals = ((timestamp(9, 9), timestamp(9, 18), "할 일"),)
        for recurring, elapsed in ((True, 0), (False, 8)):
            with self.subTest(recurring=recurring):
                calendar = business_calendar(holidays=(SlaClockHoliday(date(2025, 10, 9), recurring),))
                result = self.calculate(intervals, (completed(timestamp(9, 9), timestamp(9, 18), elapsed),), (calendar,))
                self.assertEqual({"할 일": elapsed}, self.values(result))

    def test_pause_status_normalizes_unicode_whitespace(self):
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), timestamp(8, 18), "결과\u3000대기\u00a0중"))
        self.assertEqual({"할 일": 1, "결과\u3000대기\u00a0중": 0}, self.values(self.calculate(intervals, (completed(timestamp(8, 9), timestamp(8, 18), 1),))))

    def test_unconfirmed_pause_status_is_not_excluded(self):
        intervals = ((timestamp(8, 9), timestamp(8, 18), "보류 중"),)
        result = calculate_sla_status_durations(intervals, (completed(timestamp(8, 9), timestamp(8, 18), 8),), (business_calendar(),), None, None, pause_statuses=())
        self.assertEqual({"보류 중": 8}, self.values(result))

    def test_verified_hold_pause_is_excluded_in_completed_and_ongoing_cycles_and_resumes_after_exit(self):
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), timestamp(8, 14), "보류중"), (timestamp(8, 14), timestamp(8, 16), "이슈 리뷰 중"), (timestamp(8, 16), timestamp(8, 18), "보류중"))
        cycle = completed(timestamp(8, 9), timestamp(8, 18), 3)
        for candidate in (cycle, replace(cycle, ongoing=True, paused=True, stopped_at=None)):
            with self.subTest(ongoing=candidate.ongoing):
                result = self.calculate(intervals, (candidate,), before=timestamp(8, 17), after=timestamp(8, 18))
                self.assertEqual({"할 일": 1, "보류중": 0, "이슈 리뷰 중": 2}, self.values(result))

    def test_confirmed_request_pause_is_normalized_and_clock_resumes_after_exit(self):
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), timestamp(8, 14), "자료요청중"), (timestamp(8, 14), timestamp(8, 16), "할 일"), (timestamp(8, 16), timestamp(8, 18), "결과 대기 중"))
        self.assertEqual({"할 일": 3, "자료요청중": 0, "결과 대기 중": 0}, self.values(self.calculate(intervals, (completed(timestamp(8, 9), timestamp(8, 18), 3),))))

    def test_ongoing_request_pause_matches_jira_paused_flag(self):
        before, after = timestamp(8, 11), timestamp(8, 11, 1)
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), after, "자료 요청 중"))
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=True, elapsed_ms=HOUR, started_at=timestamp(8, 9))
        self.assertEqual({"할 일": 1, "자료 요청 중": 0}, self.values(self.calculate(intervals, (cycle,), before=before, after=after)))

    def test_only_resolution_cycles_and_their_ranges_contribute(self):
        intervals = ((timestamp(8, 8), timestamp(8, 11), "할 일"), (timestamp(8, 11), timestamp(8, 18), "검토 중"))
        cycles = (replace(completed(timestamp(8, 8), timestamp(8, 11), 2), metric="initial_response"), completed(timestamp(8, 10), timestamp(8, 11), 1), completed(timestamp(8, 13), timestamp(8, 15), 2))
        self.assertEqual({"할 일": 1, "검토 중": 2}, self.values(self.calculate(intervals, cycles)))

    def test_overlapping_cycles_are_unavailable(self):
        intervals = ((timestamp(8, 9), timestamp(8, 18), "할 일"),)
        result = self.calculate(intervals, (completed(timestamp(8, 9), timestamp(8, 14), 4), completed(timestamp(8, 13), timestamp(8, 15), 2)))
        self.assertIsNone(result.durations)
        self.assertIn("겹쳐", result.warning)

    def test_zero_sla_time_is_valid_and_different_from_missing_time(self):
        intervals = ((timestamp(10, 9), timestamp(10, 18), "할 일"),)
        cycle = completed(timestamp(10, 9), timestamp(10, 18), 0)
        self.assertEqual({"할 일": 0}, self.values(self.calculate(intervals, (cycle,))))
        self.assertIsNone(self.calculate(intervals, (replace(cycle, elapsed_ms=None),)).durations)

    def test_equal_elapsed_but_different_status_allocations_are_ambiguous(self):
        intervals = ((timestamp(8, 9), timestamp(8, 12), "할 일"), (timestamp(8, 12), timestamp(8, 15), "검토 중"))
        first = business_calendar(name="Morning", working_times=(SlaClockWorkingTime(3, 9 * HOUR, 12 * HOUR),))
        second = business_calendar(id="2", name="Afternoon", working_times=(SlaClockWorkingTime(3, 12 * HOUR, 15 * HOUR),))
        result = self.calculate(intervals, (completed(timestamp(8, 9), timestamp(8, 15), 3),), (first, second))
        self.assertIsNone(result.durations)
        self.assertIn("배분이 달라", result.warning)

    def test_equivalent_calendars_can_match_without_unique_calendar_identity(self):
        intervals = ((timestamp(8, 9), timestamp(8, 18), "할 일"),)
        calendars = (business_calendar(), business_calendar(id="2", name="Also correct"))
        result = self.calculate(intervals, (completed(timestamp(8, 9), timestamp(8, 18), 8),), calendars)
        self.assertEqual({"할 일": 8}, self.values(result))
        self.assertEqual(("Tech-Ops 9-6", "Also correct"), result.calendar_names)

    def test_each_cycle_can_use_its_own_verified_calendar(self):
        intervals = ((timestamp(8, 9), timestamp(9, 18), "할 일"),)
        calendars = (business_calendar(), business_calendar(id="2", name="Morning", working_times=tuple(SlaClockWorkingTime(day, 9 * HOUR, 12 * HOUR) for day in range(5))))
        cycles = (completed(timestamp(8, 9), timestamp(8, 18), 8), completed(timestamp(9, 9), timestamp(9, 18), 3))
        result = self.calculate(intervals, cycles, calendars)
        self.assertEqual({"할 일": 11}, self.values(result))

    def test_running_cycle_adjusts_only_final_status_inside_observation_window(self):
        before, after = timestamp(8, 11), timestamp(8, 11) + timedelta(seconds=2)
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), after, "검토 중"))
        cycle = replace(completed(timestamp(8, 9), before, 2), ongoing=True, paused=False, stopped_at=None, elapsed_ms=2 * HOUR + 1250)
        result = self.calculate(intervals, (cycle,), before=before, after=after)
        self.assertEqual({"할 일": 1, "검토 중": (HOUR + 1250) / HOUR}, self.values(result))
        for elapsed in (2 * HOUR - 1, 2 * HOUR + 2001):
            with self.subTest(elapsed=elapsed):
                self.assertIsNone(self.calculate(intervals, (replace(cycle, elapsed_ms=elapsed),), before=before, after=after).durations)

    def test_running_cycle_accepts_api_millisecond_precision(self):
        before = timestamp(8, 10) + timedelta(microseconds=555)
        after = before + timedelta(milliseconds=1)
        intervals = ((timestamp(8, 9), after, "할 일"),)
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=False, elapsed_ms=HOUR, started_at=timestamp(8, 9))
        self.assertEqual({"할 일": 1}, self.values(self.calculate(intervals, (cycle,), before=before, after=after)))

    def test_running_cycle_does_not_adjust_previous_status_across_transition(self):
        before, transition, after = timestamp(8, 10), timestamp(8, 10) + timedelta(seconds=1), timestamp(8, 10) + timedelta(seconds=2)
        intervals = ((timestamp(8, 9), transition, "할 일"), (transition, after, "검토 중"))
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=False, elapsed_ms=HOUR + 1500, started_at=timestamp(8, 9))
        self.assertIsNone(self.calculate(intervals, (cycle,), before=before, after=after).durations)

    def test_paused_cycle_cannot_use_request_duration_to_hide_disagreement(self):
        before, after = timestamp(8, 10), timestamp(8, 10) + timedelta(seconds=2)
        intervals = ((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 10), after, "결과 대기 중"))
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=True, elapsed_ms=HOUR + 1, started_at=timestamp(8, 9))
        self.assertIsNone(self.calculate(intervals, (cycle,), before=before, after=after).durations)
        self.assertEqual({"할 일": 1, "결과 대기 중": 0}, self.values(self.calculate(intervals, (replace(cycle, elapsed_ms=HOUR),), before=before, after=after)))

    def test_unknown_pause_condition_does_not_produce_false_verified_allocation(self):
        before, after = timestamp(8, 19), timestamp(8, 20)
        intervals = ((timestamp(8, 9), after, "보류 중"),)
        cycle = SlaViolationCycle("resolution", None, ongoing=True, paused=True, elapsed_ms=8 * HOUR, started_at=timestamp(8, 9))
        result = calculate_sla_status_durations(intervals, (cycle,), (business_calendar(),), before, after, pause_statuses=())
        self.assertIsNone(result.durations)

    def test_invalid_missing_ranges_and_history_fail_closed(self):
        intervals = ((timestamp(8, 9), timestamp(8, 18), "할 일"),)
        cycle = completed(timestamp(8, 9), timestamp(8, 18), 8)
        for replacement in ({"started_at": None}, {"stopped_at": None}, {"started_at": timestamp(7)}, {"stopped_at": timestamp(9)}, {"elapsed_ms": -1}, {"elapsed_ms": True}, {"started_at": timestamp(8, 9).replace(tzinfo=None)}, {"ongoing": True, "stopped_at": None, "paused": False}):
            with self.subTest(replacement=replacement):
                result = self.calculate(intervals, (replace(cycle, **replacement),))
                self.assertIsNone(result.durations)
                self.assertTrue(result.warning)
        self.assertIsNone(self.calculate((), (cycle,)).durations)
        self.assertIsNone(self.calculate(((timestamp(8, 9), timestamp(8, 10), "할 일"), (timestamp(8, 11), timestamp(8, 18), "검토 중")), (cycle,)).durations)
        self.assertIsNone(self.calculate(intervals, ()).durations)

    def test_invalid_calendar_and_missing_calendars_fail_closed(self):
        intervals = ((timestamp(8, 9), timestamp(8, 18), "할 일"),)
        cycles = (completed(timestamp(8, 9), timestamp(8, 18), 8),)
        for calendar in (business_calendar(timezone="Missing/Zone"), business_calendar(working_times=(SlaClockWorkingTime(3, 18 * HOUR, 9 * HOUR),)), business_calendar(working_times=(SlaClockWorkingTime(7, 9 * HOUR, 18 * HOUR),))):
            with self.subTest(calendar=calendar):
                self.assertIsNone(self.calculate(intervals, cycles, (calendar,)).durations)
        self.assertIsNone(calculate_sla_status_durations(intervals, cycles, (), None, None).durations)

    def test_24_hour_calendar_uses_absolute_elapsed_time_through_dst(self):
        calendar = business_calendar(timezone="America/New_York", working_times=tuple(SlaClockWorkingTime(day, 0, 24 * HOUR) for day in range(7)))
        for start_text, end_text, hours in (("2026-03-08T00:00:00-05:00", "2026-03-09T00:00:00-04:00", 23), ("2026-11-01T00:00:00-04:00", "2026-11-02T00:00:00-05:00", 25)):
            with self.subTest(start=start_text):
                start, end = datetime.fromisoformat(start_text), datetime.fromisoformat(end_text)
                result = self.calculate(((start.astimezone(timezone.utc), end, "할 일"),), (completed(start, end, hours),), (calendar,))
                self.assertEqual({"할 일": hours}, self.values(result))

    def test_partial_dst_repeated_hour_counts_only_each_matching_local_window(self):
        calendar = business_calendar(timezone="America/New_York", working_times=(SlaClockWorkingTime(6, 90 * 60_000, 105 * 60_000),))
        start, end = datetime.fromisoformat("2026-11-01T00:00:00-04:00"), datetime.fromisoformat("2026-11-01T04:00:00-05:00")
        result = self.calculate(((start, end, "할 일"),), (completed(start, end, 0.5),), (calendar,))
        self.assertEqual({"할 일": 0.5}, self.values(result))

    def test_partial_dst_missing_hour_counts_only_existing_local_window(self):
        calendar = business_calendar(timezone="America/New_York", working_times=(SlaClockWorkingTime(6, 150 * 60_000, 210 * 60_000),))
        start, end = datetime.fromisoformat("2026-03-08T00:00:00-05:00"), datetime.fromisoformat("2026-03-08T04:00:00-04:00")
        result = self.calculate(((start, end, "할 일"),), (completed(start, end, 0.5),), (calendar,))
        self.assertEqual({"할 일": 0.5}, self.values(result))


if __name__ == "__main__":
    unittest.main()
