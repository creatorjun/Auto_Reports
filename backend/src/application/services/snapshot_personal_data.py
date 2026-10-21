# backend/src/application/services/snapshot_personal_data.py
import re
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Iterator

from src.domain.entities.jira_identity_history import JiraIdentityHistory, JiraUserValue, SnapshotPerson
from src.domain.entities.personal_data import PersonalDataProfile

REDACTED_PERSON = "개인정보 삭제"
UPDATING_PERSON = "사용자 정보 갱신 필요"
PERSON_FIELDS = ("reporter", "assignee", "tac_assignee", "tac_team")
_EMPTY_NAMES = frozenset({"", "미지정", "알 수 없음", REDACTED_PERSON, UPDATING_PERSON})


def is_person_name(value: object) -> bool:
    return isinstance(value, str) and value.strip() not in _EMPTY_NAMES


def valid_account_id(value: object) -> bool:
    return isinstance(value, str) and value != "unknown" and re.fullmatch(r"[A-Za-z0-9:_-]{1,128}", value) is not None


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def person_retrieved_at(payload: dict, field: str, generated_at: datetime) -> datetime:
    field_times = payload.get("personal_data_field_retrieved_at")
    values = [field_times.get(field)] if isinstance(field_times, dict) else []
    values.append(payload.get("personal_data_retrieved_at"))
    for value in values:
        if isinstance(value, str):
            try:
                return utc(datetime.fromisoformat(value))
            except ValueError:
                pass
    return utc(generated_at)


def snapshot_people(payload: object, generated_at: datetime) -> Iterator[SnapshotPerson]:
    if isinstance(payload, list):
        for item in payload:
            yield from snapshot_people(item, generated_at)
    elif isinstance(payload, dict):
        key = payload.get("key")
        if isinstance(key, str) and key:
            for field in PERSON_FIELDS:
                name = payload.get(field)
                if is_person_name(name):
                    account_id = payload.get(f"{field}_account_id")
                    yield SnapshotPerson(key, field, name, account_id if valid_account_id(account_id) else None, person_retrieved_at(payload, field, generated_at), payload)
        for value in payload.values():
            if isinstance(value, (dict, list)):
                yield from snapshot_people(value, generated_at)


def aggregate_gaps(payload: object) -> int:
    if isinstance(payload, list):
        return sum(aggregate_gaps(item) for item in payload)
    if not isinstance(payload, dict):
        return 0
    gaps = 0
    aggregates = payload.get("by_assignee")
    if isinstance(aggregates, dict):
        details = payload.get("latest_issues") or []
        counts = Counter(item.get("assignee") for item in details if isinstance(item, dict))
        gaps = sum(1 for name, count in aggregates.items() if is_person_name(name) and counts[name] != count)
    return gaps + sum(aggregate_gaps(value) for value in payload.values() if isinstance(value, (dict, list)))


def _change_snapshot_people(payload: object, change: Callable[[dict, str], bool]) -> bool:
    if isinstance(payload, list):
        changed = False
        for item in payload:
            changed = _change_snapshot_people(item, change) or changed
        return changed
    if not isinstance(payload, dict):
        return False
    aggregates = payload.get("by_assignee")
    details = payload.get("latest_issues")
    can_rebuild = isinstance(aggregates, dict) and isinstance(details, list) and (
        dict(Counter(item.get("assignee") for item in details if isinstance(item, dict))) == aggregates
    )
    changed = False
    if isinstance(payload.get("key"), str):
        for field in PERSON_FIELDS:
            changed = change(payload, field) or changed
    for value in tuple(payload.values()):
        if isinstance(value, (dict, list)):
            changed = _change_snapshot_people(value, change) or changed
    if changed and can_rebuild:
        payload["by_assignee"] = dict(Counter(item.get("assignee") for item in details if isinstance(item, dict)))
    return changed


def _mask_snapshot_people(payload: object, account_ids: set[str], label: str) -> bool:
    def change(item: dict, field: str) -> bool:
        value = item.get(field)
        if item.get(f"{field}_account_id") in account_ids and value != label and (
            is_person_name(value) or value in (REDACTED_PERSON, UPDATING_PERSON)
        ):
            item[field] = label
            return True
        return False
    return _change_snapshot_people(payload, change)


def erase_snapshot_people(payload: object, account_ids: set[str]) -> bool:
    return _mask_snapshot_people(payload, account_ids, REDACTED_PERSON)


def mark_snapshot_people_updated(payload: object, account_ids: set[str]) -> bool:
    return _mask_snapshot_people(payload, account_ids, UPDATING_PERSON)


def refresh_snapshot_people(
    payload: object, profiles: dict[str, PersonalDataProfile], generated_at: datetime,
    *, only_if_older: bool = False,
) -> bool:
    def change(item: dict, field: str) -> bool:
        profile = profiles.get(item.get(f"{field}_account_id"))
        if profile is None or field not in item:
            return False
        retrieved_at = utc(profile.retrieved_at)
        if only_if_older and item.get(field) not in (REDACTED_PERSON, UPDATING_PERSON) and (
            person_retrieved_at(item, field, generated_at) >= retrieved_at
        ):
            return False
        times = item.get("personal_data_field_retrieved_at")
        field_times = dict(times) if isinstance(times, dict) else {}
        stamp = retrieved_at.isoformat()
        if item[field] == profile.display_name and field_times.get(field) == stamp:
            return False
        item[field] = profile.display_name
        field_times[field] = stamp
        item["personal_data_field_retrieved_at"] = field_times
        return True
    return _change_snapshot_people(payload, change)


def user_at(history: JiraIdentityHistory, field_id: str, as_of: datetime) -> JiraUserValue | None:
    if not history.complete or utc(as_of) < utc(history.created_at) or field_id not in history.current_users:
        return None
    current = history.current_users[field_id]
    state = current
    selected = current
    changes = sorted((change for change in history.changes if change.field_id == field_id and utc(change.changed_at) > utc(as_of)), key=lambda change: change.changed_at, reverse=True)
    if len({change.changed_at for change in changes}) != len(changes):
        return None
    for change in changes:
        if state.account_id != change.after.account_id:
            return None
        if (is_person_name(change.after.display_name) and not valid_account_id(change.after.account_id)) or (
            is_person_name(change.before.display_name) and not valid_account_id(change.before.account_id)
        ):
            return None
        state = change.before
        selected = state
    return selected


def resolve_snapshot_account(person: SnapshotPerson, history: JiraIdentityHistory, field_ids: dict[str, tuple[str, ...]], refreshed_snapshot: bool = False) -> tuple[str | None, str]:
    if person.issue_key != history.key:
        return None, "issue_mismatch"
    if not history.complete:
        return None, "incomplete_history"
    if refreshed_snapshot:
        candidates: set[str] = set()
        for field_id in field_ids[person.field]:
            value = user_at(history, field_id, datetime.max.replace(tzinfo=timezone.utc))
            if value is None:
                return None, "unverifiable_field_history"
            values = [value]
            for change in history.changes:
                if change.field_id == field_id:
                    values.extend((change.before, change.after))
            if any(value.display_name == person.display_name and not valid_account_id(value.account_id) for value in values):
                return None, "unverifiable_field_history"
            candidates.update(value.account_id for value in values if value.display_name == person.display_name and valid_account_id(value.account_id))
        if len(candidates) == 1:
            return next(iter(candidates)), "verified"
        return None, "ambiguous_historical_name" if candidates else "name_not_in_complete_history"
    selected = None
    for field_id in field_ids[person.field]:
        value = user_at(history, field_id, person.retrieved_at)
        if value is None:
            return None, "unverifiable_field_history"
        if is_person_name(value.display_name):
            selected = value
            break
    if selected is None:
        return None, "no_user_at_snapshot"
    if selected.display_name != person.display_name:
        return None, "name_mismatch_at_snapshot"
    if not valid_account_id(selected.account_id):
        return None, "missing_account_id"
    return selected.account_id, "verified"
