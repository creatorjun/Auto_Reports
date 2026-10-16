# backend/src/domain/entities/jira_identity_history.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class JiraUserValue:
    account_id: str | None
    display_name: str | None


@dataclass(frozen=True)
class JiraUserChange:
    field_id: str
    changed_at: datetime
    before: JiraUserValue
    after: JiraUserValue


@dataclass(frozen=True)
class JiraIdentityHistory:
    key: str
    created_at: datetime
    current_users: dict[str, JiraUserValue]
    changes: tuple[JiraUserChange, ...]
    complete: bool


@dataclass(frozen=True)
class SnapshotPerson:
    issue_key: str
    field: str
    display_name: str
    account_id: str | None
    retrieved_at: datetime
    item: dict
