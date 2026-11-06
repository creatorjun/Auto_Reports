# backend/src/domain/entities/kernel_cve.py
from dataclasses import dataclass
from src.domain.entities.advisory_feed import AdvisorySeverity as KernelSeverity
from src.domain.entities.advisory_feed import AdvisorySnapshot, AdvisoryStatus as KernelStatus, SEVERITIES


@dataclass(frozen=True)
class KernelFeed:
    id: str
    label: str
    url: str
    architectures: tuple[str, ...] = ()


@dataclass(frozen=True)
class KernelTarget:
    id: str
    label: str
    packages: tuple[str, ...]
    architectures: tuple[str, ...]
    feeds: tuple[KernelFeed, ...]
    coverage: str
    available: bool = True


@dataclass(frozen=True)
class KernelBuild:
    package: str
    architecture: str
    version: str


@dataclass(frozen=True)
class KernelAdvisory:
    cve_id: str
    severity: KernelSeverity
    advisory_id: str
    advisory_url: str
    issued_at: str | None
    package: str
    architecture: str
    fixed_version: str
    branch: str = ""
    title: str = ""
    summary: str = ""


@dataclass(frozen=True)
class KernelFeedData:
    advisories: tuple[KernelAdvisory, ...]
    builds: tuple[KernelBuild, ...]
    complete: bool = True
    note: str = ""


KernelSnapshot = AdvisorySnapshot[KernelFeedData]
