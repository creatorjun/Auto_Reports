# backend/src/domain/entities/site.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Optional


class SiteStatus(StrEnum):
    INSTALLING = "구축중"
    ACTIVE     = "운영중"
    SUSPENDED  = "일시중단"
    EXPIRED    = "계약종료"


class ContractType(StrEnum):
    MAINTENANCE       = "일반유지보수"
    TECHNICAL_SUPPORT = "기술지원"
    MANAGED           = "위탁운영"


class DeploymentType(StrEnum):
    ALL_IN_ONE = "올인원"
    SEPARATED  = "분리구성"


class NodeRole(StrEnum):
    ALL_IN_ONE = "AllInOne"
    ANALYZER   = "Analyzer"
    COLLECTOR  = "Collector"


class PatchType(StrEnum):
    REGULAR   = "정기패치"
    EMERGENCY = "긴급패치"
    HOTFIX    = "핫픽스"


class PatchResultStatus(StrEnum):
    SUCCESS     = "성공"
    FAILED      = "실패"
    ROLLED_BACK = "롤백"


class VisitType(StrEnum):
    INSPECTION   = "정기점검"
    INCIDENT     = "장애대응"
    INSTALLATION = "설치"
    TRAINING     = "교육"


@dataclass
class ContactInfo:
    name:  Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Credential:
    username: str
    password: str


@dataclass
class AccessCredentials:
    cli:  Optional[Credential] = None
    web:  Optional[Credential] = None
    db:   Optional[Credential] = None
    vpn:  Optional[Credential] = None
    note: Optional[str] = None


@dataclass
class DeploymentNode:
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


@dataclass
class SolutionPackage:
    version:             Optional[str]      = None
    installer_filename:  Optional[str]      = None
    license_capacity_gb: Optional[float]    = None
    deployment_type:     Optional[DeploymentType] = None
    license_key:         Optional[str]      = None
    license_expire_date: Optional[date]     = None
    installed_at:        Optional[datetime] = None
    updated_at:          Optional[datetime] = None


@dataclass
class PatchHistory:
    issue_link:      Optional[str]             = None
    patch_date:      Optional[date]            = None
    patch_file_link: Optional[str]             = None
    patch_type:      Optional[PatchType]       = None
    applied_by:      Optional[str]             = None
    result_status:   Optional[PatchResultStatus] = None
    rollback_date:   Optional[date]            = None
    note:            Optional[str]             = None


@dataclass
class VisitHistory:
    visit_date:           Optional[date]      = None
    visitor:              Optional[str]       = None
    visit_type:           Optional[VisitType] = None
    visit_summary:        Optional[str]       = None
    next_visit_scheduled: Optional[date]      = None


@dataclass
class Site:
    site_name:           str
    id:                  Optional[int]           = None
    maintenance_company: Optional[str]           = None
    customer_contact:    Optional[ContactInfo]   = None
    maintenance_contact: Optional[ContactInfo]   = None
    contract_start_date: Optional[date]          = None
    contract_end_date:   Optional[date]          = None
    contract_type:       Optional[ContractType]  = None
    status:              Optional[SiteStatus]    = None
    nodes:               list[DeploymentNode]    = field(default_factory=list)
    solution_package:    Optional[SolutionPackage] = None
    patch_histories:     list[PatchHistory]      = field(default_factory=list)
    visit_histories:     list[VisitHistory]      = field(default_factory=list)
    access_credentials:  Optional[AccessCredentials] = None
    created_at:          datetime                = field(default_factory=datetime.utcnow)
    updated_at:          datetime                = field(default_factory=datetime.utcnow)
