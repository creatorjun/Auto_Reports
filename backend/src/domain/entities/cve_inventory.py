# backend/src/domain/entities/cve_inventory.py
from dataclasses import dataclass
from typing import Literal


CveSeverity = Literal["critical", "high", "medium", "low", "unknown"]
CveImpact = Literal["affected", "not_affected", "unknown"]
CveCollectionStatus = Literal["pending", "ok", "stale", "error", "unmapped"]


@dataclass(frozen=True)
class CveInventoryPackage:
    id: str
    name: str
    ecosystem: str
    versions: tuple[str, ...]
    product_ids: tuple[str, ...] = ()
    product_names: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    query_name: str | None = None
    query_ecosystem: str | None = None
    source: str = "osv"
    mapping_status: str = "ready"
    mapping_reason: str | None = None
    version_confidence: str = "confirmed"
    distribution_id: str | None = None
    distribution_version: str | None = None
    rpm_vendor: str | None = None


@dataclass(frozen=True)
class CveInventory:
    dataset_id: str
    snapshot_at: str | None
    packages: tuple[CveInventoryPackage, ...]
    product_count: int
    target_count: int
    runtime_verified: bool = False


@dataclass(frozen=True)
class CveVersionRange:
    affected: str
    fixed: str | None = None
    type: str = "ECOSYSTEM"


@dataclass(frozen=True)
class CveFinding:
    cve_id: str
    title: str
    affected_versions: tuple[str, ...] = ()
    fixed_versions: tuple[str, ...] = ()
    ranges: tuple[CveVersionRange, ...] = ()
    severity: CveSeverity = "unknown"
    cvss_score: float | None = None
    cvss_version: str | None = None
    references: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    published_at: str | None = None
    modified_at: str | None = None
    inventory_impact: CveImpact = "unknown"
    affected_inventory_versions: tuple[str, ...] = ()
    first_seen_at: str | None = None
    known_exploited: bool = False
    severity_source: str | None = None


@dataclass(frozen=True)
class CvePackageSnapshot:
    package_id: str
    findings: tuple[CveFinding, ...] = ()
    status: CveCollectionStatus = "pending"
    last_success_at: str | None = None
    last_attempt_at: str | None = None
    error: str | None = None
    first_seen: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class CveStoredSnapshot:
    dataset_id: str
    packages: tuple[CvePackageSnapshot, ...]
    last_attempt_at: str | None = None
    refreshed_at: str | None = None
    initialized: bool = False
