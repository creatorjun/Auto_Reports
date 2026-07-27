# backend/src/presentation/api/v1/sites.py
from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.site_use_cases import SiteUseCase
from src.domain.entities.site import (
    ContactInfo,
    ContractType,
    DeploymentNode,
    DeploymentType,
    NodeRole,
    PatchHistory,
    PatchResultStatus,
    PatchType,
    Site,
    SiteStatus,
    SolutionPackage,
    VisitHistory,
    VisitType,
)
from src.presentation.api.v1.deps import get_site_use_case
from src.presentation.schemas.site_schema import (
    SiteCreateRequest,
    SiteResponse,
    SiteUpdateRequest,
)

router = APIRouter(prefix="/sites", tags=["sites"])


def _to_domain(req: SiteCreateRequest) -> Site:
    return Site(
        id=req.id,
        site_name=req.site_name,
        maintenance_company=req.maintenance_company,
        customer_info=ContactInfo(
            name=req.customer_info.name,
            phone=req.customer_info.phone,
            email=req.customer_info.email,
        ),
        maintenance_info=ContactInfo(
            name=req.maintenance_info.name,
            phone=req.maintenance_info.phone,
            email=req.maintenance_info.email,
        ),
        contract_start_date=req.contract_start_date,
        contract_end_date=req.contract_end_date,
        contract_type=req.contract_type,
        status=req.status,
        nodes=[
            DeploymentNode(
                id=n.id,
                site_id=req.id,
                hostname=n.hostname,
                role=n.role,
                cpu_cores=n.cpu_cores,
                cpu_threads=n.cpu_threads,
                memory_total_gb=n.memory_total_gb,
                disk_total_gb=n.disk_total_gb,
                os_type=n.os_type,
                os_version=n.os_version,
                ip_address=n.ip_address,
                disk_free_gb=n.disk_free_gb,
                disk_updated_at=n.disk_updated_at,
            )
            for n in req.nodes
        ],
        solution_package=(
            SolutionPackage(
                id=req.solution_package.id,
                site_id=req.id,
                version=req.solution_package.version,
                installer_filename=req.solution_package.installer_filename,
                license_capacity_gb=req.solution_package.license_capacity_gb,
                deployment_type=req.solution_package.deployment_type,
                license_key=req.solution_package.license_key,
                license_expire_date=req.solution_package.license_expire_date,
                installed_at=req.solution_package.installed_at,
                updated_at=req.solution_package.updated_at,
            )
            if req.solution_package
            else None
        ),
        patch_histories=[
            PatchHistory(
                id=p.id,
                site_id=req.id,
                issue_link=p.issue_link,
                patch_date=p.patch_date,
                patch_file_link=p.patch_file_link,
                patch_type=p.patch_type,
                applied_by=p.applied_by,
                result_status=p.result_status,
                rollback_date=p.rollback_date,
                note=p.note,
            )
            for p in req.patch_histories
        ],
        visit_histories=[
            VisitHistory(
                id=v.id,
                site_id=req.id,
                visit_date=v.visit_date,
                visitor=v.visitor,
                visit_type=v.visit_type,
                visit_summary=v.visit_summary,
                next_visit_scheduled=v.next_visit_scheduled,
            )
            for v in req.visit_histories
        ],
    )


def _to_response(site: Site) -> SiteResponse:
    from src.presentation.schemas.site_schema import (
        ContactInfoSchema,
        DeploymentNodeSchema,
        PatchHistorySchema,
        SolutionPackageSchema,
        VisitHistorySchema,
    )

    return SiteResponse(
        id=site.id,
        site_name=site.site_name,
        maintenance_company=site.maintenance_company,
        customer_info=ContactInfoSchema(**site.customer_info.__dict__),
        maintenance_info=ContactInfoSchema(**site.maintenance_info.__dict__),
        contract_start_date=site.contract_start_date,
        contract_end_date=site.contract_end_date,
        contract_type=site.contract_type,
        status=site.status,
        created_at=site.created_at,
        updated_at=site.updated_at,
        nodes=[DeploymentNodeSchema(**n.__dict__) for n in site.nodes],
        solution_package=(
            SolutionPackageSchema(**site.solution_package.__dict__)
            if site.solution_package
            else None
        ),
        patch_histories=[PatchHistorySchema(**p.__dict__) for p in site.patch_histories],
        visit_histories=[VisitHistorySchema(**v.__dict__) for v in site.visit_histories],
    )


@router.get("/", response_model=list[SiteResponse])
async def list_sites(use_case: SiteUseCase = Depends(get_site_use_case)):
    sites = await use_case.get_all()
    return [_to_response(s) for s in sites]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return _to_response(site)


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(
    body: SiteCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    try:
        site = await use_case.create(_to_domain(body))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _to_response(site)


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: str,
    body: SiteUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    existing = await use_case.get_by_id(site_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found")

    updated = Site(
        id=existing.id,
        site_name=body.site_name if body.site_name is not None else existing.site_name,
        maintenance_company=(
            body.maintenance_company
            if body.maintenance_company is not None
            else existing.maintenance_company
        ),
        customer_info=(
            ContactInfo(
                name=body.customer_info.name,
                phone=body.customer_info.phone,
                email=body.customer_info.email,
            )
            if body.customer_info is not None
            else existing.customer_info
        ),
        maintenance_info=(
            ContactInfo(
                name=body.maintenance_info.name,
                phone=body.maintenance_info.phone,
                email=body.maintenance_info.email,
            )
            if body.maintenance_info is not None
            else existing.maintenance_info
        ),
        contract_start_date=(
            body.contract_start_date
            if body.contract_start_date is not None
            else existing.contract_start_date
        ),
        contract_end_date=(
            body.contract_end_date
            if body.contract_end_date is not None
            else existing.contract_end_date
        ),
        contract_type=(
            body.contract_type if body.contract_type is not None else existing.contract_type
        ),
        status=body.status if body.status is not None else existing.status,
        nodes=existing.nodes,
        solution_package=existing.solution_package,
        patch_histories=existing.patch_histories,
        visit_histories=existing.visit_histories,
    )
    site = await use_case.update(updated)
    return _to_response(site)


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: str,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete(site_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Site not found")
