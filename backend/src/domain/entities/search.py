# backend/src/domain/entities/search.py
from dataclasses import dataclass
from enum import StrEnum


class SearchSource(StrEnum):
    JIRA = "jira"
    CONFLUENCE = "confluence"


@dataclass(frozen=True)
class SearchResult:
    source: SearchSource
    key: str
    title: str
    status: str
    item_type: str
    url: str
