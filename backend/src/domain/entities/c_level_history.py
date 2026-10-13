# backend/src/domain/entities/c_level_history.py
from dataclasses import dataclass


@dataclass(frozen=True)
class CLevelComment:
    issue_key: str
    delay_reason: str = ""
    action_taken: str = ""
    prevention_plan: str = ""
    included: bool = True
    updated_by: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class CLevelSnapshotSummary:
    id: int
    title: str
    period: str
    start_date: str
    end_date: str
    as_of: str
    saved_by: str
    saved_at: str
