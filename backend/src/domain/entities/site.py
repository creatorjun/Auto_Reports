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
    OFFICIAL  = "\uc815\uc2dd\ub77c\uc774\uc13c\uc2a4"
    TEMPORARY = "\uc784\uc2dc\ub77c\uc774\uc13c\uc2a4"


class DeploymentType(StrEnum):
    ALL_IN_ONE = "\uc62c\uc778\uc6d0"
    SEPARATED  = "\ubd84\ub9ac\uad6c\uc131"


class NodeRole(StrEnum):
    ALL_IN_ONE = "AllInOne"
    ANALYZER   = "Analyzer"
    COLLECTOR  = "Collector"
    PROXY      = "Proxy"


class PatchType(StrEnum):
    REGULAR   = "\uc815\uae30\ud328\uce58"
    EMERGENCY = "\uae34\uae09\ud328\uce58"
    HOTFIX    = "\ud56f\ud53d\uc2a4"


class PatchResultStatus(StrEnum):
    SUCCESS     = "\uc131\uacf5"
    FAILED      = "\uc2e4\ud328"
    ROLLED_BACK = "\ub864\ubc31"


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


@dataclass(frozen=True)
class SolutionPackage:
    id:                  Optional[int]           = None
    version:             Optional[str]            = None
    installer_filename:  Optional[str]            = None
    license_capacity_gb: Optional[float]          = None
    deployment_type:     Optional[DeploymentType] = None
    license_key:         Optional[str]            = None
    license_expire_date: Optional[date]           = None
    installed_at:        Optional[datetime]       = None
    updated_at:          Optional[datetime]       = None


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
    solution_package:    Optional[SolutionPackage]   = None
    patch_histories:     list[PatchHistory]          = field(default_factory=list)
    visit_histories:     list[VisitHistory]          = field(default_factory=list)
    access_credentials:  Optional[AccessCredentials] = None
    created_at:          datetime                    = field(default_factory=_utc_now)
    updated_at:          datetime                    = field(default_factory=_utc_now)
