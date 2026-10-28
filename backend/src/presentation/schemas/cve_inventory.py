# backend/src/presentation/schemas/cve_inventory.py
from pydantic import BaseModel

from src.domain.entities.cve_inventory import CveCollectionStatus, CveImpact, CveSeverity


class CveVersionRangeResponse(BaseModel):
    affected: str
    fixed: str | None
    type: str


class CveInventoryItemResponse(BaseModel):
    id: str
    package_id: str
    package_name: str
    ecosystem: str
    inventory_versions: tuple[str, ...]
    product_names: tuple[str, ...]
    categories: tuple[str, ...]
    cve_id: str
    title: str
    affected_versions: tuple[str, ...]
    fixed_versions: tuple[str, ...]
    ranges: tuple[CveVersionRangeResponse, ...]
    severity: CveSeverity
    cvss_score: float | None
    cvss_version: str | None
    references: tuple[str, ...]
    source_ids: tuple[str, ...]
    source: str
    published_at: str | None
    modified_at: str | None
    inventory_impact: CveImpact
    affected_inventory_versions: tuple[str, ...]
    first_seen_at: str | None
    known_exploited: bool
    severity_source: str | None
    collection_status: CveCollectionStatus


class CveInventoryMetadataResponse(BaseModel):
    dataset_id: str
    snapshot_at: str | None
    product_count: int
    target_count: int
    package_count: int
    runtime_verified: bool


class CveInventoryCoverageResponse(BaseModel):
    total: int
    ready: int
    unmapped: int
    ok: int
    stale: int
    error: int
    pending: int


class CveSeverityCountsResponse(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    unknown: int


class CveRefreshProgressResponse(BaseModel):
    completed: int
    total: int


class CveInventoryResponse(BaseModel):
    items: tuple[CveInventoryItemResponse, ...]
    total: int
    page: int
    page_size: int
    severity_counts: CveSeverityCountsResponse
    inventory: CveInventoryMetadataResponse
    coverage: CveInventoryCoverageResponse
    ecosystems: tuple[str, ...]
    initialized: bool
    refreshing: bool
    refreshed_at: str | None
    next_refresh_at: str | None
    retry_after_seconds: int
    refresh_interval_seconds: int
    progress: CveRefreshProgressResponse
    error: str | None


class CveInventoryPackageResponse(BaseModel):
    id: str
    name: str
    ecosystem: str
    versions: tuple[str, ...]
    product_names: tuple[str, ...]
    categories: tuple[str, ...]
    source: str
    mapping_status: str
    mapping_reason: str | None
    status: CveCollectionStatus
    last_success_at: str | None
    last_attempt_at: str | None
    error: str | None
    cve_count: int


class CveInventoryPackagesResponse(BaseModel):
    items: tuple[CveInventoryPackageResponse, ...]
    total: int
    page: int
    page_size: int
