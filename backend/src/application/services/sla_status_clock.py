# backend/src/application/services/sla_status_clock.py
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.domain.entities.sla_clock import SlaClockAllocation, SlaClockCalendar
from src.domain.entities.sla_violation_report import SlaStatusDuration, SlaViolationCycle


_UTC = timezone.utc
_DAY_MS = 86_400_000
_HOUR_US = 3_600_000_000


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("SLA clock 계산 시각에 시간대가 없습니다.")
    return value.astimezone(_UTC)


def _microseconds(delta: timedelta) -> int:
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _normalized(status: str) -> str:
    return "".join(unicodedata.normalize("NFKC", status).split())


def _offset_segments(start: datetime, end: datetime, zone: ZoneInfo) -> tuple[tuple[datetime, datetime, timedelta], ...]:
    segments = []
    cursor = start
    segment_start = start
    offset = start.astimezone(zone).utcoffset()
    while cursor < end:
        next_cursor = min(cursor + timedelta(hours=1), end)
        next_offset = next_cursor.astimezone(zone).utcoffset()
        if next_offset != offset:
            lower, upper = 0, _microseconds(next_cursor - cursor)
            while upper - lower > 1:
                middle = (lower + upper) // 2
                if (cursor + timedelta(microseconds=middle)).astimezone(zone).utcoffset() == offset:
                    lower = middle
                else:
                    upper = middle
            boundary = cursor + timedelta(microseconds=upper)
            segments.append((segment_start, boundary, offset))
            segment_start, offset = boundary, next_offset
        cursor = next_cursor
    if segment_start < end:
        segments.append((segment_start, end, offset))
    return tuple(segments)


@lru_cache(maxsize=8192)
def _calendar_windows(calendar: SlaClockCalendar, day: date) -> tuple[tuple[datetime, datetime], ...]:
    if any(holiday.day == day or (holiday.recurring and (holiday.day.month, holiday.day.day) == (day.month, day.day)) for holiday in calendar.holidays):
        return ()
    working_times = tuple(window for window in calendar.working_times if window.weekday == day.weekday())
    if not working_times:
        return ()
    zone = ZoneInfo(calendar.timezone)
    local_start = datetime.combine(day, time.min)
    local_end = local_start + timedelta(days=1)
    start = min(local_start.replace(tzinfo=zone, fold=fold).astimezone(_UTC) for fold in (0, 1))
    end = max(local_end.replace(tzinfo=zone, fold=fold).astimezone(_UTC) for fold in (0, 1))
    windows = []
    for segment_start, segment_end, offset in _offset_segments(start, end, zone):
        for working_time in working_times:
            window_start = (local_start + timedelta(milliseconds=working_time.start_ms) - offset).replace(tzinfo=_UTC)
            window_end = (local_start + timedelta(milliseconds=working_time.end_ms) - offset).replace(tzinfo=_UTC)
            overlap_start, overlap_end = max(segment_start, window_start), min(segment_end, window_end)
            if overlap_start < overlap_end:
                windows.append((overlap_start, overlap_end))
    merged = []
    for window_start, window_end in sorted(windows):
        if merged and window_start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], window_end))
        else:
            merged.append((window_start, window_end))
    return tuple(merged)


def _working_microseconds(calendar: SlaClockCalendar, start: datetime, end: datetime) -> int:
    zone = ZoneInfo(calendar.timezone)
    day = start.astimezone(zone).date()
    final_day = end.astimezone(zone).date()
    total = 0
    while day <= final_day:
        for window_start, window_end in _calendar_windows(calendar, day):
            overlap_start, overlap_end = max(start, window_start), min(end, window_end)
            if overlap_start < overlap_end:
                total += _microseconds(overlap_end - overlap_start)
        day += timedelta(days=1)
    return total


def _validate_calendars(calendars: tuple[SlaClockCalendar, ...]) -> None:
    if not calendars:
        raise ValueError("Jira SLA 캘린더를 조회할 수 없어 상태별 SLA 시간을 확인할 수 없습니다.")
    for calendar in calendars:
        try:
            ZoneInfo(calendar.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
            raise ValueError("Jira SLA 캘린더의 시간대가 유효하지 않습니다.") from error
        for window in calendar.working_times:
            if any(type(value) is not int for value in (window.weekday, window.start_ms, window.end_ms)) or not (0 <= window.weekday <= 6 and 0 <= window.start_ms < window.end_ms <= _DAY_MS):
                raise ValueError("Jira SLA 캘린더의 업무시간 설정이 유효하지 않습니다.")
        if any(type(holiday.day) is not date or type(holiday.recurring) is not bool for holiday in calendar.holidays):
            raise ValueError("Jira SLA 캘린더의 휴일 설정이 유효하지 않습니다.")


def _validated_intervals(intervals: tuple[tuple[datetime, datetime, str], ...]) -> tuple[tuple[datetime, datetime, str], ...]:
    if not intervals:
        raise ValueError("상태 이력이 없어 상태별 SLA 시간을 확인할 수 없습니다.")
    result = []
    for start, end, status in intervals:
        start, end = _utc(start), _utc(end)
        if not isinstance(status, str) or not _normalized(status) or start > end or (result and result[-1][1] != start):
            raise ValueError("상태 이력이 연속되지 않아 상태별 SLA 시간을 확인할 수 없습니다.")
        result.append((start, end, status))
    return tuple(result)


def _allocation(
    intervals: tuple[tuple[datetime, datetime, str], ...],
    calendar: SlaClockCalendar,
    start: datetime,
    end: datetime,
    pause_statuses: frozenset[str],
) -> dict[str, int]:
    totals = dict.fromkeys((status for _, _, status in intervals), 0)
    for interval_start, interval_end, status in intervals:
        overlap_start, overlap_end = max(start, interval_start), min(end, interval_end)
        if overlap_start < overlap_end and _normalized(status) not in pause_statuses:
            totals[status] += _working_microseconds(calendar, overlap_start, overlap_end)
    return totals


def _cycle_allocation(
    intervals: tuple[tuple[datetime, datetime, str], ...],
    calendar: SlaClockCalendar,
    cycle: SlaViolationCycle,
    start: datetime,
    lower_end: datetime,
    upper_end: datetime,
    pause_statuses: frozenset[str],
) -> dict[str, int] | None:
    lower = _allocation(intervals, calendar, start, lower_end, pause_statuses)
    expected_us = cycle.elapsed_ms * 1000
    if not cycle.ongoing:
        return lower if sum(lower.values()) == expected_us else None
    upper = _allocation(intervals, calendar, start, upper_end, pause_statuses)
    final_status = next(status for interval_start, interval_end, status in reversed(intervals) if interval_start <= upper_end <= interval_end)
    if cycle.paused != (_normalized(final_status) in pause_statuses):
        return None
    if cycle.paused:
        return lower if lower == upper and sum(lower.values()) == expected_us else None
    if any(lower[status] != upper[status] for status in lower if status != final_status):
        return None
    adjusted_us = expected_us - sum(value for status, value in lower.items() if status != final_status)
    lower_ms, upper_ms = lower[final_status] // 1000, upper[final_status] // 1000
    if adjusted_us < 0 or not lower_ms <= adjusted_us // 1000 <= upper_ms:
        return None
    lower[final_status] = adjusted_us
    return lower


def calculate_sla_status_durations(
    intervals: tuple[tuple[datetime, datetime, str], ...],
    cycles: tuple[SlaViolationCycle, ...],
    calendars: tuple[SlaClockCalendar, ...],
    snapshot_before: datetime | None,
    snapshot_after: datetime | None,
    pause_statuses: tuple[str, ...] = ("결과 대기 중", "자료 요청 중", "보류 중"),
) -> SlaClockAllocation:
    try:
        intervals = _validated_intervals(intervals)
        _validate_calendars(calendars)
        resolution_cycles = tuple(cycle for cycle in cycles if cycle.metric == "resolution")
        if not resolution_cycles:
            raise ValueError("해결시간 SLA 사이클이 없어 상태별 SLA 시간을 확인할 수 없습니다.")
        before = _utc(snapshot_before) if snapshot_before is not None else None
        after = _utc(snapshot_after) if snapshot_after is not None else None
        if before is not None and after is not None and before > after:
            raise ValueError("Jira SLA 수집 시각의 순서가 유효하지 않습니다.")
        paused = frozenset(_normalized(status) for status in pause_statuses)
        prepared = []
        for cycle in resolution_cycles:
            if cycle.started_at is None or type(cycle.elapsed_ms) is not int or cycle.elapsed_ms < 0:
                raise ValueError("해결시간 SLA의 시작 시각 또는 누적 시간이 누락되어 상태별 SLA 시간을 확인할 수 없습니다.")
            start = _utc(cycle.started_at)
            if cycle.ongoing:
                if before is None or after is None or type(cycle.paused) is not bool or cycle.stopped_at is not None:
                    raise ValueError("진행 중인 해결시간 SLA의 수집 시각 또는 정지 상태를 확인할 수 없습니다.")
                lower_end, upper_end = max(start, before), after
            else:
                if cycle.stopped_at is None:
                    raise ValueError("종료된 해결시간 SLA의 종료 시각을 확인할 수 없습니다.")
                lower_end = upper_end = _utc(cycle.stopped_at)
            if start > upper_end or start < intervals[0][0] or upper_end > intervals[-1][1] or (after is not None and upper_end > after):
                raise ValueError("해결시간 SLA 사이클과 상태 이력의 시각 범위가 일치하지 않습니다.")
            prepared.append((start, lower_end, upper_end, cycle))
        prepared.sort(key=lambda item: item[0])
        if sum(cycle.ongoing for _, _, _, cycle in prepared) > 1 or any(previous[2] > current[0] for previous, current in zip(prepared, prepared[1:])):
            raise ValueError("해결시간 SLA 사이클이 겹쳐 상태별 SLA 시간을 중복 없이 계산할 수 없습니다.")
        totals = dict.fromkeys((status for _, _, status in intervals), 0)
        matched_names = []
        for start, lower_end, upper_end, cycle in prepared:
            matches = []
            for calendar in calendars:
                allocation = _cycle_allocation(intervals, calendar, cycle, start, lower_end, upper_end, paused)
                if allocation is not None:
                    matches.append((calendar.name, allocation))
            if not matches:
                raise ValueError("Jira 해결시간 SLA 누적 시간과 캘린더 계산이 일치하지 않아 상태별 SLA 시간을 확인할 수 없습니다.")
            if any(allocation != matches[0][1] for _, allocation in matches[1:]):
                raise ValueError("Jira SLA 캘린더별 상태 시간 배분이 달라 적용 캘린더를 확정할 수 없습니다.")
            for status, value in matches[0][1].items():
                totals[status] += value
            matched_names.extend(name for name, _ in matches)
        durations = tuple(SlaStatusDuration(status, value / _HOUR_US) for status, value in totals.items())
        return SlaClockAllocation(durations, tuple(dict.fromkeys(matched_names)))
    except ValueError as error:
        return SlaClockAllocation(None, warning=str(error))
