# backend/src/presentation/schemas/site_schema.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from src.domain.entities.site import (
    ContractType,
    DeploymentType,
    NodeRole,
    PatchResultStatus,
    PatchType,
    SiteStatus,
    VisitType,
)


class ContactInfoSchema(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None


class DeploymentNodeSchema(BaseModel):
    id: Optional[int] = None
    hostname: str
    role: NodeRole
    cpu_cores: int
    cpu_threads: int
    memory_total_gb: int
    disk_total_gb: int
    os_type: str
    os_version: str
    ip_address: Optional[str] = None
    disk_free_gb: Optional[int] = None
    disk_updated_at: Optional[datetime] = None


class SolutionPackageSchema(BaseModel):
    id: Optional[int] = None
    version: str
    installer_filename: str
    license_capacity_gb: float
    deployment_type: DeploymentType
    license_key: Optional[str] = None
    license_expire_date: Optional[date] = None
    installed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PatchHistorySchema(BaseModel):
    id: Optional[int] = None
    issue_link: str
    patch_date: date
    patch_file_link: str
    patch_type: PatchType
    applied_by: str
    result_status: PatchResultStatus
    rollback_date: Optional[date] = None
    note: Optional[str] = None


class VisitHistorySchema(BaseModel):
    id: Optional[int] = None
    visit_date: date
    visitor: str
    visit_type: VisitType
    visit_summary: str
    next_visit_scheduled: Optional[date] = None


class SiteSummaryResponse(BaseModel):
    id: str
    site_name: str
    customer_name: str
    status: str
    contract_end_date: date

    model_config = {"from_attributes": True}


class SiteCreateRequest(BaseModel):
    id: str
    site_name: str
    maintenance_company: str
    customer_info: ContactInfoSchema
    maintenance_info: ContactInfoSchema
    contract_start_date: date
    contract_end_date: date
    contract_type: ContractType
    status: SiteStatus
    nodes: list[DeploymentNodeSchema] = []
    solution_package: Optional[SolutionPackageSchema] = None
    patch_histories: list[PatchHistorySchema] = []
    visit_histories: list[VisitHistorySchema] = []


class SiteUpdateRequest(BaseModel):
    site_name: Optional[str] = None
    maintenance_company: Optional[str] = None
    customer_info: Optional[ContactInfoSchema] = None
    maintenance_info: Optional[ContactInfoSchema] = None
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    contract_type: Optional[ContractType] = None
    status: Optional[SiteStatus] = None


class SiteResponse(BaseModel):
    id: str
    site_name: str
    maintenance_company: str
    customer_info: ContactInfoSchema
    maintenance_info: ContactInfoSchema
    contract_start_date: date
    contract_end_date: date
    contract_type: ContractType
    status: SiteStatus
    created_at: datetime
    updated_at: datetime
    nodes: list[DeploymentNodeSchema] = []
    solution_package: Optional[SolutionPackageSchema] = None
    patch_histories: list[PatchHistorySchema] = []
    visit_histories: list[VisitHistorySchema] = []

    model_config = {"from_attributes": True}
