# backend/src/infrastructure/external/jira_sla_calendar.py
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.domain.entities.sla_clock import SlaClockCalendar, SlaClockHoliday, SlaClockWorkingTime


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def calendar_ids_for_project(payload: object, project_id: str) -> tuple[str, ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("calendars"), list):
        raise ValueError("Jira SLA 캘린더 목록이 유효하지 않습니다.")
    entries = payload["calendars"]
    if any(not isinstance(entry, dict) or not isinstance(entry.get("context"), dict) for entry in entries):
        raise ValueError("Jira SLA 캘린더 프로젝트 정보가 유효하지 않습니다.")
    desks = {
        str(entry["context"]["serviceDeskId"])
        for entry in entries
        if str(entry["context"].get("projectId", "")) == project_id and entry["context"].get("serviceDeskId") is not None
    }
    ids = []
    for entry in entries:
        context = entry["context"]
        if str(context.get("projectId", "")) != project_id and str(context.get("serviceDeskId", "")) not in desks:
            continue
        identifier = str(entry.get("id", ""))
        if not identifier.isdecimal():
            raise ValueError("Jira SLA 캘린더 식별자가 유효하지 않습니다.")
        ids.append(identifier)
    return tuple(dict.fromkeys(ids))


def parse_clock_calendar(payload: object, expected_id: str) -> SlaClockCalendar:
    if not isinstance(payload, dict) or str(payload.get("id", "")) != expected_id:
        raise ValueError("Jira SLA 캘린더 응답이 유효하지 않습니다.")
    name, timezone = payload.get("name"), payload.get("timezoneId")
    if not isinstance(name, str) or not name.strip() or not isinstance(timezone, str):
        raise ValueError("Jira SLA 캘린더 이름 또는 시간대가 누락되었습니다.")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Jira SLA 캘린더 시간대가 유효하지 않습니다.") from error
    if not isinstance(payload.get("workingTimes"), list) or not isinstance(payload.get("holidays"), list):
        raise ValueError("Jira SLA 근무시간 또는 휴일 목록이 누락되었습니다.")
    times = []
    for value in payload["workingTimes"]:
        if not isinstance(value, dict) or value.get("weekday") not in _WEEKDAYS:
            raise ValueError("Jira SLA 근무 요일이 유효하지 않습니다.")
        start, end = value.get("start"), value.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= 86_400_000:
            raise ValueError("Jira SLA 근무시간 구간이 유효하지 않습니다.")
        times.append(SlaClockWorkingTime(_WEEKDAYS.index(value["weekday"]), start, end))
    holidays = []
    for value in payload["holidays"]:
        if not isinstance(value, dict) or type(value.get("recurring")) is not bool:
            raise ValueError("Jira SLA 휴일 설정이 유효하지 않습니다.")
        raw_date = value.get("iso8601Date")
        if not isinstance(raw_date, str):
            raise ValueError("Jira SLA 휴일 날짜가 누락되었습니다.")
        holidays.append(SlaClockHoliday(date.fromisoformat(raw_date), value["recurring"]))
    return SlaClockCalendar(expected_id, name, timezone, tuple(times), tuple(holidays))
