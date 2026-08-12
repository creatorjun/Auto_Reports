# backend/src/presentation/api/v1/sites.py
from fastapi import APIRouter, Depends, HTTPException, Query

from src.presentation.mappers.site_mapper import (
    contact_from_schema,
    creds_from_schema,
    node_to_schema,
    patch_to_schema,
    site_to_response,
    site_to_summary,
    visit_to_schema,
)
from src.application.use_cases.site_use_cases import SiteUseCase
from src.domain.entities.site import (
    DeploymentNode,
    NodeRole,
    PatchHistory,
    VisitHistory,
)
from src.presentation.api.v1.deps import get_site_use_case
from src.presentation.schemas.site_schema import (
    DeploymentNodeCreateRequest,
    DeploymentNodeUpdateRequest,
    PatchHistoryCreateRequest,
    PatchHistoryUpdateRequest,
    SiteCreateRequest,
    SiteResponse,
    SiteSummaryResponse,
    SiteUpdateRequest,
    VisitHistoryCreateRequest,
    VisitHistoryUpdateRequest,
)

router = APIRouter(prefix="/sites", tags=["sites"])


def _to_domain(req: SiteCreateRequest):
    from src.domain.entities.site import Site
    return Site(
        site_name=req.site_name,
        maintenance_company=req.maintenance_company,
        customer_contact=contact_from_schema(req.customer_info),
        maintenance_contact=contact_from_schema(req.maintenance_info),
        contract_start_date=req.contract_start_date,
        contract_end_date=req.contract_end_date,
        contract_type=req.contract_type,
        status=req.status,
        nodes=[
            DeploymentNode(
                hostname=n.hostname,
                role=NodeRole(n.role) if n.role else None,
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
        patch_histories=[
            PatchHistory(
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
                visit_datetime=v.visit_datetime,
                engineer_name=v.engineer_name,
                engineer_phone=v.engineer_phone,
                request_content=v.request_content,
                action_content=v.action_content,
            )
            for v in req.visit_histories
        ],
        access_credentials=creds_from_schema(req.access_credentials),
    )


@router.get("/search", response_model=list[SiteSummaryResponse])
async def search_sites(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    dtos = await use_case.search(q, limit)
    return [site_to_summary(d) for d in dtos]


@router.get("/recent", response_model=list[SiteSummaryResponse])
async def get_recent_sites(
    limit: int = Query(5, ge=1, le=50),
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    dtos = await use_case.get_recent(limit)
    return [site_to_summary(d) for d in dtos]


@router.get("/", response_model=list[SiteSummaryResponse])
async def list_sites(
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    sites = await use_case.get_all()
    return [site_to_summary(s) for s in sites]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return site_to_response(site)


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(
    req: SiteCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.create(_to_domain(req))
    return site_to_response(site)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    req: SiteUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    updates: dict[str, object] = {}
    if req.site_name is not None:
        updates["site_name"] = req.site_name
    if req.maintenance_company is not None:
        updates["maintenance_company"] = req.maintenance_company
    if req.customer_info is not None:
        updates["customer_contact"] = contact_from_schema(req.customer_info)
    if req.maintenance_info is not None:
        updates["maintenance_contact"] = contact_from_schema(req.maintenance_info)
    if req.contract_start_date is not None:
        updates["contract_start_date"] = req.contract_start_date
    if req.contract_end_date is not None:
        updates["contract_end_date"] = req.contract_end_date
    if req.contract_type is not None:
        updates["contract_type"] = req.contract_type
    if req.status is not None:
        updates["status"] = req.status
    if req.access_credentials is not None:
        updates["access_credentials"] = creds_from_schema(req.access_credentials)

    site = await use_case.update_fields(site_id, updates)
    return site_to_response(site)


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete(site_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Site not found")


@router.post("/{site_id}/nodes", response_model=SiteResponse, status_code=201)
async def add_node(
    site_id: int,
    req: DeploymentNodeCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    node = DeploymentNode(
        hostname=req.hostname,
        role=NodeRole(req.role) if req.role else None,
        cpu_cores=req.cpu_cores,
        cpu_threads=req.cpu_threads,
        memory_total_gb=req.memory_total_gb,
        disk_total_gb=req.disk_total_gb,
        os_type=req.os_type,
        os_version=req.os_version,
        ip_address=req.ip_address,
        disk_free_gb=req.disk_free_gb,
        disk_updated_at=req.disk_updated_at,
    )
    site = await use_case.add_node(site_id, node)
    return site_to_response(site)


@router.patch("/{site_id}/nodes/{node_id}", response_model=SiteResponse)
async def update_node(
    site_id: int,
    node_id: int,
    req: DeploymentNodeUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    updates = req.model_dump(exclude_unset=True)
    updated_site = await use_case.update_node(site_id, node_id, updates)
    return site_to_response(updated_site)


@router.delete("/{site_id}/nodes/{node_id}", status_code=204)
async def delete_node(
    site_id: int,
    node_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    await use_case.delete_node(site_id, node_id)


@router.post("/{site_id}/patch-histories", response_model=SiteResponse, status_code=201)
async def add_patch_history(
    site_id: int,
    req: PatchHistoryCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    ph = PatchHistory(
        issue_link=req.issue_link,
        patch_date=req.patch_date,
        patch_file_link=req.patch_file_link,
        patch_type=req.patch_type,
        applied_by=req.applied_by,
        result_status=req.result_status,
        rollback_date=req.rollback_date,
        note=req.note,
    )
    site = await use_case.add_patch_history(site_id, ph)
    return site_to_response(site)


@router.patch("/{site_id}/patch-histories/{ph_id}", response_model=SiteResponse)
async def update_patch_history(
    site_id: int,
    ph_id: int,
    req: PatchHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    updates = req.model_dump(exclude_unset=True)
    updated_site = await use_case.update_patch_history(site_id, ph_id, updates)
    return site_to_response(updated_site)


@router.delete("/{site_id}/patch-histories/{ph_id}", status_code=204)
async def delete_patch_history(
    site_id: int,
    ph_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    await use_case.delete_patch_history(site_id, ph_id)


@router.post("/{site_id}/visit-histories", response_model=SiteResponse, status_code=201)
async def add_visit_history(
    site_id: int,
    req: VisitHistoryCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    vh = VisitHistory(
        visit_datetime=req.visit_datetime,
        engineer_name=req.engineer_name,
        engineer_phone=req.engineer_phone,
        request_content=req.request_content,
        action_content=req.action_content,
    )
    site = await use_case.add_visit_history(site_id, vh)
    return site_to_response(site)


@router.patch("/{site_id}/visit-histories/{vh_id}", response_model=SiteResponse)
async def update_visit_history(
    site_id: int,
    vh_id: int,
    req: VisitHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    updates = req.model_dump(exclude_unset=True)
    updated_site = await use_case.update_visit_history(site_id, vh_id, updates)
    return site_to_response(updated_site)


@router.delete("/{site_id}/visit-histories/{vh_id}", status_code=204)
async def delete_visit_history(
    site_id: int,
    vh_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    await use_case.delete_visit_history(site_id, vh_id)
