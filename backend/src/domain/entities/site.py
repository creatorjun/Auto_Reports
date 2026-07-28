# backend/src/domain/entities/site.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Optional


class SiteStatus(StrEnum):
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
    name:  str
    phone: str
    email: Optional[str] = None


@dataclass
class Credential:
    username: str
    password: str


@dataclass
class AccessCredentials:
    cli: Optional[Credential] = None
    web: Optional[Credential] = None
    db:  Optional[Credential] = None
    vpn: Optional[Credential] = None
    note: Optional[str] = None


@dataclass
class DeploymentNode:
    hostname:        str
    role:            NodeRole
    cpu_cores:       int
    cpu_threads:     int
    memory_total_gb: int
    disk_total_gb:   int
    os_type:         str
    os_version:      str
    ip_address:      Optional[str]      = None
    disk_free_gb:    Optional[int]      = None
    disk_updated_at: Optional[datetime] = None


@dataclass
class SolutionPackage:
    version:             str
    installer_filename:  str
    license_capacity_gb: float
    deployment_type:     DeploymentType
    license_key:         Optional[str]      = None
    license_expire_date: Optional[date]     = None
    installed_at:        Optional[datetime] = None
    updated_at:          Optional[datetime] = None


@dataclass
class PatchHistory:
    issue_link:      str
    patch_date:      date
    patch_file_link: str
    patch_type:      PatchType         = PatchType.REGULAR
    applied_by:      str               = ""
    result_status:   PatchResultStatus = PatchResultStatus.SUCCESS
    rollback_date:   Optional[date]    = None
    note:            Optional[str]     = None


@dataclass
class VisitHistory:
    visit_date:           date
    visitor:              str
    visit_type:           VisitType
    visit_summary:        str
    next_visit_scheduled: Optional[date] = None


@dataclass
class Site:
    id:                  str
    site_name:           str
    maintenance_company: str
    customer_contact:    ContactInfo
    maintenance_contact: ContactInfo
    contract_start_date: date
    contract_end_date:   date
    contract_type:       ContractType
    status:              SiteStatus
    nodes:               list[DeploymentNode]      = field(default_factory=list)
    solution_package:    Optional[SolutionPackage] = None
    patch_histories:     list[PatchHistory]        = field(default_factory=list)
    visit_histories:     list[VisitHistory]        = field(default_factory=list)
    access_credentials:  Optional[AccessCredentials] = None
    created_at:          datetime                  = field(default_factory=datetime.utcnow)
    updated_at:          datetime                  = field(default_factory=datetime.utcnow)
