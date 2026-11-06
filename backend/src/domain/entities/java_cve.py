# backend/src/domain/entities/java_cve.py
from dataclasses import dataclass


@dataclass(frozen=True)
class JavaFeed:
    id: str
    label: str
    url: str
    releases_only: bool = False


@dataclass(frozen=True)
class JavaTarget:
    id: str
    label: str
    feeds: tuple[JavaFeed, ...]
    coverage: str
    available: bool = True


@dataclass(frozen=True)
class JavaBuild:
    version: str
    major: int
    label: str = ""
    channel: str = ""
    issued_at: str | None = None


@dataclass(frozen=True)
class JavaAdvisory:
    cve_id: str
    severity: str
    advisory_id: str
    advisory_url: str
    issued_at: str | None
    major: int
    fixed_version: str | None = None
    title: str = ""
    summary: str = ""
    affected_through: str | None = None
    affected_version: str | None = None
    component: str = ""
    cvss_score: float | None = None
    channel: str = ""


@dataclass(frozen=True)
class JavaFeedData:
    advisories: tuple[JavaAdvisory, ...]
    builds: tuple[JavaBuild, ...]
    complete: bool = True
    note: str = ""
