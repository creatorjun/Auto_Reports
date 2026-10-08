# backend/src/application/services/stage_duration.py
from datetime import datetime

from src.application.ports.jira_port import JiraStatusChange
from src.domain.constants import KST


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    return timestamp.replace(tzinfo=KST) if timestamp.tzinfo is None else timestamp.astimezone(KST)


def stage_duration_hours(
    created: str,
    resolved: str,
    current_status: str,
    changes: list[JiraStatusChange],
) -> dict[str, float]:
    start = parse_timestamp(created)
    end = parse_timestamp(resolved)
    if end < start:
        raise ValueError("Issue resolution precedes creation")
    ordered = sorted(
        ((parse_timestamp(change.changed_at), change) for change in changes),
        key=lambda entry: entry[0],
    )
    status = ordered[0][1].from_status if ordered else current_status
    if not status:
        raise ValueError("Issue initial status is missing")
    cursor = start
    hours: dict[str, float] = {}
    for changed_at, change in ordered:
        if changed_at < start:
            status = change.to_status
            continue
        if changed_at > end:
            break
        if change.from_status != status or not change.to_status:
            raise ValueError(
                f"Issue status history is incomplete at {change.changed_at}: "
                f"expected from_status={status!r}, "
                f"got from_status={change.from_status!r}, to_status={change.to_status!r}"
            )
        elapsed = (changed_at - cursor).total_seconds() / 3600
        if elapsed > 0:
            hours[status] = hours.get(status, 0) + elapsed
        status = change.to_status
        cursor = changed_at
    elapsed = (end - cursor).total_seconds() / 3600
    if elapsed > 0:
        hours[status] = hours.get(status, 0) + elapsed
    return hours
