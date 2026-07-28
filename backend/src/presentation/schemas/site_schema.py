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
)


class ContactInfoSchema(BaseModel):
    name:  Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CredentialSchema(BaseModel):
    username: str
    password: str
    ip:       Optional[str] = None
    port:     Optional[str] = None


class AccessCredentialsSchema(BaseModel):
    cli:  Optional[CredentialSchema] = None
    web:  Optional[CredentialSchema] = None
    db:   Optional[CredentialSchema] = None
    vpn:  Optional[CredentialSchema] = None
    note: Optional[str] = None


class DeploymentNodeSchema(BaseModel):
    id:              Optional[int]          = None
    hostname:        Optional[str]          = None
    role:            Optional[NodeRole]     = None
    cpu_cores:       Optional[int]          = None
    cpu_threads:     Optional[int]          = None
    memory_total_gb: Optional[int]          = None
    disk_total_gb:   Optional[int]          = None
    os_type:         Optional[str]          = None
    os_version:      Optional[str]          = None
    ip_address:      Optional[str]          = None
    disk_free_gb:    Optional[int]          = None
    disk_updated_at: Optional[datetime]     = None


class SolutionPackageSchema(BaseModel):
    id:                  Optional[int]            = None
    version:             Optional[str]            = None
    installer_filename:  Optional[str]            = None
    license_capacity_gb: Optional[float]          = None
    deployment_type:     Optional[DeploymentType] = None
    license_key:         Optional[str]            = None
    license_expire_date: Optional[date]           = None
    installed_at:        Optional[datetime]        = None
    updated_at:          Optional[datetime]        = None


class PatchHistorySchema(BaseModel):
    id:              Optional[int]               = None
    issue_link:      Optional[str]               = None
    patch_date:      Optional[date]              = None
    patch_file_link: Optional[str]               = None
    patch_type:      Optional[PatchType]         = None
    applied_by:      Optional[str]               = None
    result_status:   Optional[PatchResultStatus] = None
    rollback_date:   Optional[date]              = None
    note:            Optional[str]               = None


class PatchHistoryCreateRequest(BaseModel):
    issue_link:      Optional[str]               = None
    patch_date:      Optional[date]              = None
    patch_file_link: Optional[str]               = None
    patch_type:      Optional[PatchType]         = None
    applied_by:      Optional[str]               = None
    result_status:   Optional[PatchResultStatus] = None
    rollback_date:   Optional[date]              = None
    note:            Optional[str]               = None


class PatchHistoryUpdateRequest(BaseModel):
    issue_link:      Optional[str]               = None
    patch_date:      Optional[date]              = None
    patch_file_link: Optional[str]               = None
    patch_type:      Optional[PatchType]         = None
    applied_by:      Optional[str]               = None
    result_status:   Optional[PatchResultStatus] = None
    rollback_date:   Optional[date]              = None
    note:            Optional[str]               = None


class VisitHistorySchema(BaseModel):
    id:               Optional[int]      = None
    visit_datetime:   Optional[datetime] = None
    engineer_name:    Optional[str]      = None
    engineer_phone:   Optional[str]      = None
    request_content:  Optional[str]      = None
    action_content:   Optional[str]      = None


class VisitHistoryCreateRequest(BaseModel):
    visit_datetime:   Optional[datetime] = None
    engineer_name:    Optional[str]      = None
    engineer_phone:   Optional[str]      = None
    request_content:  Optional[str]      = None
    action_content:   Optional[str]      = None


class VisitHistoryUpdateRequest(BaseModel):
    visit_datetime:   Optional[datetime] = None
    engineer_name:    Optional[str]      = None
    engineer_phone:   Optional[str]      = None
    request_content:  Optional[str]      = None
    action_content:   Optional[str]      = None


class SiteSummaryResponse(BaseModel):
    id:                int
    site_name:         str
    customer_name:     Optional[str] = None
    status:            Optional[str] = None
    contract_end_date: Optional[date] = None

    model_config = {"from_attributes": True}


class SiteCreateRequest(BaseModel):
    site_name:           str
    maintenance_company: Optional[str]                      = None
    customer_info:       Optional[ContactInfoSchema]        = None
    maintenance_info:    Optional[ContactInfoSchema]        = None
    contract_start_date: Optional[date]                     = None
    contract_end_date:   Optional[date]                     = None
    contract_type:       Optional[ContractType]             = None
    status:              Optional[SiteStatus]               = None
    nodes:               list[DeploymentNodeSchema]         = []
    solution_package:    Optional[SolutionPackageSchema]    = None
    patch_histories:     list[PatchHistorySchema]           = []
    visit_histories:     list[VisitHistorySchema]           = []
    access_credentials:  Optional[AccessCredentialsSchema]  = None


class SiteUpdateRequest(BaseModel):
    site_name:           Optional[str]                      = None
    maintenance_company: Optional[str]                      = None
    customer_info:       Optional[ContactInfoSchema]        = None
    maintenance_info:    Optional[ContactInfoSchema]        = None
    contract_start_date: Optional[date]                     = None
    contract_end_date:   Optional[date]                     = None
    contract_type:       Optional[ContractType]             = None
    status:              Optional[SiteStatus]               = None
    access_credentials:  Optional[AccessCredentialsSchema]  = None


class SiteResponse(BaseModel):
    id:                  int
    site_name:           str
    maintenance_company: Optional[str]                      = None
    customer_info:       Optional[ContactInfoSchema]        = None
    maintenance_info:    Optional[ContactInfoSchema]        = None
    contract_start_date: Optional[date]                     = None
    contract_end_date:   Optional[date]                     = None
    contract_type:       Optional[ContractType]             = None
    status:              Optional[SiteStatus]               = None
    created_at:          datetime
    updated_at:          datetime
    nodes:               list[DeploymentNodeSchema]         = []
    solution_package:    Optional[SolutionPackageSchema]    = None
    patch_histories:     list[PatchHistorySchema]           = []
    visit_histories:     list[VisitHistorySchema]           = []
    access_credentials:  Optional[AccessCredentialsSchema]  = None

    model_config = {"from_attributes": True}
