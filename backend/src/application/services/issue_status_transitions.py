# backend/src/application/services/issue_status_transitions.py
from datetime import datetime

from src.application.ports.jira_port import JiraStatusChange
from src.domain.constants import KST


def transition_datetime(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("Issue status transition date is invalid") from error
    if instant.tzinfo is None:
        raise ValueError("Issue status transition date requires a timezone")
    return instant.astimezone(KST)


def latest_status_transitions(
    changes: list[JiraStatusChange], status_names: dict[str, str],
) -> dict[str, str]:
    latest: dict[str, datetime] = {}
    for change in changes:
        instant = transition_datetime(change.changed_at)
        name = status_names.get(change.to_status_id) or change.to_status
        if not name:
            raise ValueError("Issue status transition destination is missing")
        if change.to_status_id and change.to_status_id == change.from_status_id:
            continue
        if not change.to_status_id and change.to_status == change.from_status:
            continue
        if name not in latest or instant > latest[name]:
            latest[name] = instant
    return {name: instant.isoformat() for name, instant in latest.items()}


def status_transition_days(transitions: dict[str, dict[str, str]], now: datetime) -> dict[str, dict[str, int]]:
    today = now.astimezone(KST).date()
    return {
        key: {
            name: max(0, (today - transition_datetime(instant).date()).days)
            for name, instant in statuses.items()
        }
        for key, statuses in transitions.items()
    }
