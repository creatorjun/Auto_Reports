# backend/src/application/ports/issue_query.py
from dataclasses import dataclass
from enum import StrEnum


class IssueOrder(StrEnum):
    NONE = "none"
    NEWEST = "newest"
    NEWEST_WITH_KEY = "newest_with_key"
    OLDEST_WITH_KEY = "oldest_with_key"


@dataclass(frozen=True)
class IssueSelection:
    project: str | None = None
    reporters: tuple[str, ...] | None = None
    reporter: str | None = None
    keys: tuple[str, ...] | None = None
    updated_within_minutes: int | None = None
    order: IssueOrder = IssueOrder.NONE


IssueQuery = str | IssueSelection
