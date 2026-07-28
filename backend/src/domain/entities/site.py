# backend/src/domain/entities/site.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
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


class DeploymentType(StrEnum):
    ALL_IN_ONE = "올인원"
    SEPARATED  = "분리구성"


class PatchType(StrEnum):
    REGULAR   = "정기패치"
    EMERGENCY = "긴급패치"
    HOTFIX    = "핫픽스"


class PatchResultStatus(StrEnum):
    SUCCESS     = "성공"
    FAILED      = "실패"
    ROLLED_BACK = "롤백"


@dataclass
class ContactInfo:
    name:    Optional[str] = None
    phone:   Optional[str] = None
    email:   Optional[str] = None
    company: Optional[str] = None


@dataclass
class Credential:
    username: str
    password: str
    ip:       Optional[str] = None
    port:     Optional[str] = None


@dataclass
class AccessCredentials:
    cli:  Optional[Credential] = None
    web:  Optional[Credential] = None
    db:   Optional[Credential] = None
    vpn:  Optional[Credential] = None
    note: Optional[str] = None


@dataclass
class DeploymentNode:
    id:          Optional[int] = None
    purpose:     Optional[str] = None
    cpu_cores:   Optional[int] = None
    cpu_threads: Optional[int] = None
    ram_gb:      Optional[int] = None
    storage_gb:  Optional[int] = None


@dataclass
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


@dataclass
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


@dataclass
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
    id:                  Optional[int]              = None
    maintenance_company: Optional[str]              = None
    customer_contact:    Optional[ContactInfo]      = None
    maintenance_contact: Optional[ContactInfo]      = None
    contract_start_date: Optional[date]             = None
    contract_end_date:   Optional[date]             = None
    contract_type:       Optional[ContractType]     = None
    status:              Optional[SiteStatus]       = None
    nodes:               list[DeploymentNode]       = field(default_factory=list)
    solution_package:    Optional[SolutionPackage]  = None
    patch_histories:     list[PatchHistory]         = field(default_factory=list)
    visit_histories:     list[VisitHistory]         = field(default_factory=list)
    access_credentials:  Optional[AccessCredentials] = None
    created_at:          datetime                   = field(default_factory=datetime.utcnow)
    updated_at:          datetime                   = field(default_factory=datetime.utcnow)
