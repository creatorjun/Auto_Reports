# backend/src/domain/entities/site.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Optional


class SiteStatus(StrEnum):
    INSTALLING  = "installing"
    ACTIVE      = "active"
    INACTIVE    = "inactive"
    EXPIRED     = "expired"
    MAINTENANCE = "maintenance"


class ContractType(StrEnum):
    OFFICIAL  = "정식라이센스"
    TEMPORARY = "임시라이센스"


class NodeRole(StrEnum):
    ALL_IN_ONE = "AllInOne"
    ANALYZER   = "Analyzer"
    COLLECTOR  = "Collector"
    PROXY      = "Proxy"


class PatchType(StrEnum):
    REGULAR   = "정기패치"
    EMERGENCY = "긴급패치"
    HOTFIX    = "핫픽스"


class PatchResultStatus(StrEnum):
    SUCCESS     = "성공"
    FAILED      = "실패"
    ROLLED_BACK = "롤백"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ContactInfo:
    name:    Optional[str] = None
    phone:   Optional[str] = None
    email:   Optional[str] = None
    company: Optional[str] = None


@dataclass(frozen=True)
class Credential:
    username: str
    password: str
    ip:       Optional[str] = None
    port:     Optional[str] = None


@dataclass(frozen=True)
class AccessCredentials:
    cli:  Optional[Credential] = None
    web:  Optional[Credential] = None
    db:   Optional[Credential] = None
    vpn:  Optional[Credential] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class DeploymentNode:
    id:              Optional[int]      = None
    hostname:        Optional[str]      = None
    role:            Optional[NodeRole] = None
    cpu_cores:       Optional[int]      = None
    cpu_threads:     Optional[int]      = None
    memory_total_gb: Optional[int]      = None
    disk_total_gb:   Optional[int]      = None
    os_type:         Optional[str]      = None
    os_version:      Optional[str]      = None
    ip_address:      Optional[str]      = None
    disk_free_gb:    Optional[int]      = None
    disk_updated_at: Optional[datetime] = None
    pkg_version:     Optional[str]      = None


@dataclass(frozen=True)
class PatchHistory:
    id:              Optional[int]               = None
    issue_link:      Optional[str]               = None
    patch_date:      Optional[date]              = None
    patch_file_link: Optional[str]               = None
    patch_type:      Optional[PatchType]         = None
    applied_by:      Optional[str]               = None
    result_status:   Optional[PatchResultStatus] = None
    rollback_date:   Optional[date]              = None
    note:            Optional[str]               = None


@dataclass(frozen=True)
class VisitHistory:
    id:               Optional[int]      = None
    visit_datetime:   Optional[datetime] = None
    engineer_name:    Optional[str]      = None
    engineer_phone:   Optional[str]      = None
    request_content:  Optional[str]      = None
    action_content:   Optional[str]      = None


@dataclass
class Site:
    site_name:           str
    id:                  Optional[int]               = None
    maintenance_company: Optional[str]               = None
    customer_contact:    Optional[ContactInfo]       = None
    maintenance_contact: Optional[ContactInfo]       = None
    contract_start_date: Optional[date]              = None
    contract_end_date:   Optional[date]              = None
    contract_type:       Optional[ContractType]      = None
    status:              Optional[SiteStatus]        = None
    nodes:               list[DeploymentNode]        = field(default_factory=list)
    patch_histories:     list[PatchHistory]          = field(default_factory=list)
    visit_histories:     list[VisitHistory]          = field(default_factory=list)
    access_credentials:  Optional[AccessCredentials] = None
    created_at:          datetime                    = field(default_factory=_utc_now)
    updated_at:          datetime                    = field(default_factory=_utc_now)


@dataclass(frozen=True)
class SiteSummary:
    id:                int
    site_name:         str
    customer_name:     Optional[str] = None
    status:            Optional[SiteStatus] = None
    contract_end_date: Optional[date] = None
