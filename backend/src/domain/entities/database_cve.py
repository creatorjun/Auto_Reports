# backend/src/domain/entities/database_cve.py
from dataclasses import dataclass

from src.domain.entities.advisory_feed import AdvisorySeverity


@dataclass(frozen=True)
class DatabaseFeed:
    id: str
    label: str
    url: str
    releases_only: bool = False


@dataclass(frozen=True)
class DatabaseTarget:
    id: str
    label: str
    feeds: tuple[DatabaseFeed, ...]
    coverage: str
    available: bool = True


@dataclass(frozen=True)
class DatabaseBuild:
    version: str
    series: str
    label: str = ""
    issued_at: str | None = None
    channel: str = ""
    supported: bool | None = None


@dataclass(frozen=True)
class DatabaseAdvisory:
    cve_id: str
    severity: AdvisorySeverity
    advisory_id: str
    advisory_url: str
    issued_at: str | None
    series: str
    fixed_version: str | None = None
    title: str = ""
    summary: str = ""
    affected_through: str | None = None
    affected_version: str | None = None
    affected_from: str | None = None
    component: str = ""
    cvss_score: float | None = None
    channel: str = ""
    affected_from_inclusive: bool = True
    affected_through_inclusive: bool = True


@dataclass(frozen=True)
class DatabaseFeedData:
    advisories: tuple[DatabaseAdvisory, ...]
    builds: tuple[DatabaseBuild, ...]
    complete: bool = True
    note: str = ""
