# backend/src/application/services/c_level_timeline.py
from dataclasses import dataclass
from datetime import datetime

from src.application.services.c_level_periods import local_time
from src.domain.entities.c_level_report import CLevelIssue, CLevelStatus


_OWNERS = {
    "할 일": "TAC", "재오픈": "TAC", "이슈 리뷰 중": "TAC", "배포 파일 검토 중": "TAC",
    "자료 요청 중": "고객·파트너", "결과 대기 중": "고객·파트너",
    "연구소 대기 중": "연구소", "연구소 검토 중": "연구소", "구현 중": "연구소", "처리 중": "연구소",
}


def status_owner(status: CLevelStatus) -> str:
    return _OWNERS.get(status.name, "기타")


def same_status(first: CLevelStatus, second: CLevelStatus) -> bool:
    return first.id == second.id if first.id and second.id else first.name == second.name


@dataclass(frozen=True)
class CLevelInterval:
    status: CLevelStatus
    start: datetime
    end: datetime


@dataclass(frozen=True)
class CLevelHistory:
    status: CLevelStatus | None
    intervals: tuple[CLevelInterval, ...]
    done_entries: tuple[datetime, ...]
    reopen_count: int | None
    complete: bool
    warnings: tuple[str, ...] = ()
    unknown_transition_times: tuple[datetime, ...] = ()


def reconstruct_history(issue: CLevelIssue, as_of: datetime) -> CLevelHistory:
    as_of, created_at = local_time(as_of), local_time(issue.created_at)
    if created_at >= as_of:
        return CLevelHistory(None, (), (), 0, True)
    if not issue.history_complete:
        return CLevelHistory(None, (), (), None, False, (f"{issue.key}: 상태 이력이 불완전하여 과거 상태와 완료 집계를 확인할 수 없습니다.",))
    changes = sorted(issue.status_changes, key=lambda change: local_time(change.changed_at))
    known_categories = {"new", "indeterminate", "done"}
    known_statuses = {
        status.id: status
        for status in (issue.status, *(status for change in changes for status in (change.from_status, change.to_status)))
        if status.id and status.category in known_categories
    }

    def resolved_status(status: CLevelStatus) -> CLevelStatus:
        return known_statuses.get(status.id, status)

    status = resolved_status(changes[0].from_status if changes else issue.status)
    intervals: list[CLevelInterval] = []
    done_entries: list[datetime] = []
    unknown_transitions: list[datetime] = []
    reopened = 0
    cursor = created_at
    for change in changes:
        changed_at = local_time(change.changed_at)
        if changed_at >= as_of:
            break
        if changed_at < created_at or not same_status(status, change.from_status):
            return CLevelHistory(None, (), (), None, False, (f"{issue.key}: 상태 전환 이력의 연속성을 확인할 수 없습니다.",))
        to_status = resolved_status(change.to_status)
        if changed_at > cursor:
            intervals.append(CLevelInterval(status, cursor, changed_at))
        if status.category in known_categories and to_status.category in known_categories:
            if status.category != "done" and to_status.category == "done":
                done_entries.append(changed_at)
            if status.category == "done" and to_status.category != "done":
                reopened += 1
        else:
            unknown_transitions.append(changed_at)
        status, cursor = to_status, changed_at
    if cursor < as_of:
        intervals.append(CLevelInterval(status, cursor, as_of))
    warnings = (f"{issue.key}: 일부 과거 상태 범주가 없어 해당 전환이 포함된 기간의 완료 건수와 재오픈 횟수는 확인 불가입니다.",) if unknown_transitions or status.category not in known_categories else ()
    return CLevelHistory(status, tuple(intervals), tuple(done_entries), None if unknown_transitions else reopened, True, warnings, tuple(unknown_transitions))


def interval_at(history: CLevelHistory, timestamp: datetime | None) -> CLevelInterval | None:
    if timestamp is None or not history.complete:
        return None
    at = local_time(timestamp)
    return next((interval for interval in history.intervals if interval.start <= at < interval.end), None)
