# backend/src/presentation/api/v1/sites.py
from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.use_cases.site_use_cases import SiteUseCase
from src.domain.entities.site import (
    AccessCredentials,
    ContactInfo,
    Credential,
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
)
from src.presentation.api.v1.deps import get_site_use_case
from src.presentation.schemas.site_schema import (
    AccessCredentialsSchema,
    ContactInfoSchema,
    CredentialSchema,
    DeploymentNodeSchema,
    PatchHistorySchema,
    PatchHistoryCreateRequest,
    PatchHistoryUpdateRequest,
    SiteCreateRequest,
    SiteResponse,
    SiteSummaryResponse,
    SiteUpdateRequest,
    SolutionPackageSchema,
    VisitHistorySchema,
    VisitHistoryCreateRequest,
    VisitHistoryUpdateRequest,
)

router = APIRouter(prefix="/sites", tags=["sites"])


def _creds_from_schema(schema: AccessCredentialsSchema | None) -> AccessCredentials | None:
    if schema is None:
        return None
    return AccessCredentials(
        cli=Credential(username=schema.cli.username, password=schema.cli.password, ip=schema.cli.ip, port=schema.cli.port) if schema.cli else None,
        web=Credential(username=schema.web.username, password=schema.web.password, ip=schema.web.ip, port=schema.web.port) if schema.web else None,
        db=Credential(username=schema.db.username,  password=schema.db.password,  ip=schema.db.ip,  port=schema.db.port)  if schema.db  else None,
        vpn=Credential(username=schema.vpn.username, password=schema.vpn.password, ip=schema.vpn.ip, port=schema.vpn.port) if schema.vpn else None,
        note=schema.note,
    )


def _creds_to_schema(creds: AccessCredentials | None) -> AccessCredentialsSchema | None:
    if creds is None:
        return None
    return AccessCredentialsSchema(
        cli=CredentialSchema(username=creds.cli.username, password=creds.cli.password, ip=creds.cli.ip, port=creds.cli.port) if creds.cli else None,
        web=CredentialSchema(username=creds.web.username, password=creds.web.password, ip=creds.web.ip, port=creds.web.port) if creds.web else None,
        db=CredentialSchema(username=creds.db.username,  password=creds.db.password,  ip=creds.db.ip,  port=creds.db.port)  if creds.db  else None,
        vpn=CredentialSchema(username=creds.vpn.username, password=creds.vpn.password, ip=creds.vpn.ip, port=creds.vpn.port) if creds.vpn else None,
        note=creds.note,
    )


def _contact_from_schema(s: ContactInfoSchema | None) -> ContactInfo | None:
    if s is None:
        return None
    return ContactInfo(name=s.name, phone=s.phone, email=s.email, company=s.company)


def _contact_to_schema(c: ContactInfo | None) -> ContactInfoSchema | None:
    if c is None:
        return None
    return ContactInfoSchema(name=c.name, phone=c.phone, email=c.email, company=c.company)


def _node_to_schema(n: DeploymentNode) -> DeploymentNodeSchema:
    return DeploymentNodeSchema(
        id=n.id,
        hostname=n.hostname,
        role=n.role.value if n.role else None,
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


def _to_domain(req: SiteCreateRequest) -> Site:
    return Site(
        site_name=req.site_name,
        maintenance_company=req.maintenance_company,
        customer_contact=_contact_from_schema(req.customer_info),
        maintenance_contact=_contact_from_schema(req.maintenance_info),
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
        solution_package=(
            SolutionPackage(
                version=req.solution_package.version,
                installer_filename=req.solution_package.installer_filename,
                license_capacity_gb=req.solution_package.license_capacity_gb,
                deployment_type=req.solution_package.deployment_type,
                license_key=req.solution_package.license_key,
                license_expire_date=req.solution_package.license_expire_date,
                installed_at=req.solution_package.installed_at,
                updated_at=req.solution_package.updated_at,
            )
            if req.solution_package else None
        ),
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
        access_credentials=_creds_from_schema(req.access_credentials),
    )


def _to_response(site: Site) -> SiteResponse:
    return SiteResponse(
        id=site.id,
        site_name=site.site_name,
        maintenance_company=site.maintenance_company,
        customer_info=_contact_to_schema(site.customer_contact),
        maintenance_info=_contact_to_schema(site.maintenance_contact),
        contract_start_date=site.contract_start_date,
        contract_end_date=site.contract_end_date,
        contract_type=site.contract_type.value if site.contract_type else None,
        status=site.status.value if site.status else None,
        created_at=site.created_at,
        updated_at=site.updated_at,
        nodes=[_node_to_schema(n) for n in site.nodes],
        solution_package=(
            SolutionPackageSchema(
                id=site.solution_package.id,
                version=site.solution_package.version,
                installer_filename=site.solution_package.installer_filename,
                license_capacity_gb=site.solution_package.license_capacity_gb,
                deployment_type=site.solution_package.deployment_type.value if site.solution_package.deployment_type else None,
                license_key=site.solution_package.license_key,
                license_expire_date=site.solution_package.license_expire_date,
                installed_at=site.solution_package.installed_at,
                updated_at=site.solution_package.updated_at,
            )
            if site.solution_package else None
        ),
        patch_histories=[
            PatchHistorySchema(
                id=p.id,
                issue_link=p.issue_link,
                patch_date=p.patch_date,
                patch_file_link=p.patch_file_link,
                patch_type=p.patch_type.value if p.patch_type else None,
                applied_by=p.applied_by,
                result_status=p.result_status.value if p.result_status else None,
                rollback_date=p.rollback_date,
                note=p.note,
            )
            for p in site.patch_histories
        ],
        visit_histories=[
            VisitHistorySchema(
                id=v.id,
                visit_datetime=v.visit_datetime,
                engineer_name=v.engineer_name,
                engineer_phone=v.engineer_phone,
                request_content=v.request_content,
                action_content=v.action_content,
            )
            for v in site.visit_histories
        ],
        access_credentials=_creds_to_schema(site.access_credentials),
    )


@router.get("/search", response_model=list[SiteSummaryResponse])
async def search_sites(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    dtos = await use_case.search(q, limit)
    return [
        SiteSummaryResponse(id=d.id, site_name=d.site_name, customer_name=d.customer_name,
                            status=d.status, contract_end_date=d.contract_end_date)
        for d in dtos
    ]


@router.get("/recent", response_model=list[SiteSummaryResponse])
async def get_recent_sites(
    limit: int = Query(5, ge=1, le=20),
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    dtos = await use_case.get_recent(limit)
    return [
        SiteSummaryResponse(id=d.id, site_name=d.site_name, customer_name=d.customer_name,
                            status=d.status, contract_end_date=d.contract_end_date)
        for d in dtos
    ]


@router.get("/", response_model=list[SiteResponse])
async def list_sites(use_case: SiteUseCase = Depends(get_site_use_case)):
    return [_to_response(s) for s in await use_case.get_all()]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: int, use_case: SiteUseCase = Depends(get_site_use_case)):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return _to_response(site)


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(body: SiteCreateRequest, use_case: SiteUseCase = Depends(get_site_use_case)):
    try:
        site = await use_case.create(_to_domain(body))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _to_response(site)


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    body: SiteUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    existing = await use_case.get_by_id(site_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found")
    updated = Site(
        id=existing.id,
        site_name=body.site_name if body.site_name is not None else existing.site_name,
        maintenance_company=body.maintenance_company if body.maintenance_company is not None else existing.maintenance_company,
        customer_contact=_contact_from_schema(body.customer_info) if body.customer_info is not None else existing.customer_contact,
        maintenance_contact=_contact_from_schema(body.maintenance_info) if body.maintenance_info is not None else existing.maintenance_contact,
        contract_start_date=body.contract_start_date if body.contract_start_date is not None else existing.contract_start_date,
        contract_end_date=body.contract_end_date if body.contract_end_date is not None else existing.contract_end_date,
        contract_type=body.contract_type if body.contract_type is not None else existing.contract_type,
        status=body.status if body.status is not None else existing.status,
        nodes=existing.nodes,
        solution_package=existing.solution_package,
        patch_histories=existing.patch_histories,
        visit_histories=existing.visit_histories,
        access_credentials=_creds_from_schema(body.access_credentials) if body.access_credentials is not None else existing.access_credentials,
    )
    return _to_response(await use_case.update(updated))


@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: int, use_case: SiteUseCase = Depends(get_site_use_case)):
    if not await use_case.delete(site_id):
        raise HTTPException(status_code=404, detail="Site not found")


@router.post("/{site_id}/patch_histories", response_model=PatchHistorySchema, status_code=201)
async def add_patch_history(
    site_id: int,
    body: PatchHistoryCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    patch = PatchHistory(
        issue_link=body.issue_link,
        patch_date=body.patch_date,
        patch_file_link=body.patch_file_link,
        patch_type=body.patch_type,
        applied_by=body.applied_by,
        result_status=body.result_status,
        rollback_date=body.rollback_date,
        note=body.note,
    )
    updated_site = await use_case.add_patch_history(site_id, patch)
    p = max(updated_site.patch_histories, key=lambda x: x.id or 0)
    return PatchHistorySchema(
        id=p.id,
        issue_link=p.issue_link,
        patch_date=p.patch_date,
        patch_file_link=p.patch_file_link,
        patch_type=p.patch_type.value if p.patch_type else None,
        applied_by=p.applied_by,
        result_status=p.result_status.value if p.result_status else None,
        rollback_date=p.rollback_date,
        note=p.note,
    )


@router.put("/{site_id}/patch_histories/{patch_id}", response_model=PatchHistorySchema)
async def update_patch_history(
    site_id: int,
    patch_id: int,
    body: PatchHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    patch = next((p for p in site.patch_histories if p.id == patch_id), None)
    if not patch:
        raise HTTPException(status_code=404, detail="PatchHistory not found")
    if body.issue_link      is not None: patch.issue_link      = body.issue_link
    if body.patch_date      is not None: patch.patch_date      = body.patch_date
    if body.patch_file_link is not None: patch.patch_file_link = body.patch_file_link
    if body.patch_type      is not None: patch.patch_type      = body.patch_type
    if body.applied_by      is not None: patch.applied_by      = body.applied_by
    if body.result_status   is not None: patch.result_status   = body.result_status
    if body.rollback_date   is not None: patch.rollback_date   = body.rollback_date
    if body.note            is not None: patch.note            = body.note
    updated_site = await use_case.update(site)
    p = next(p for p in updated_site.patch_histories if p.id == patch_id)
    return PatchHistorySchema(
        id=p.id,
        issue_link=p.issue_link,
        patch_date=p.patch_date,
        patch_file_link=p.patch_file_link,
        patch_type=p.patch_type.value if p.patch_type else None,
        applied_by=p.applied_by,
        result_status=p.result_status.value if p.result_status else None,
        rollback_date=p.rollback_date,
        note=p.note,
    )


@router.delete("/{site_id}/patch_histories/{patch_id}", status_code=204)
async def delete_patch_history(
    site_id: int,
    patch_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    original_len = len(site.patch_histories)
    site.patch_histories = [p for p in site.patch_histories if p.id != patch_id]
    if len(site.patch_histories) == original_len:
        raise HTTPException(status_code=404, detail="PatchHistory not found")
    await use_case.update(site)


@router.post("/{site_id}/visit_histories", response_model=VisitHistorySchema, status_code=201)
async def add_visit_history(
    site_id: int,
    body: VisitHistoryCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    visit = VisitHistory(
        visit_datetime=body.visit_datetime,
        engineer_name=body.engineer_name,
        engineer_phone=body.engineer_phone,
        request_content=body.request_content,
        action_content=body.action_content,
    )
    updated_site = await use_case.add_visit_history(site_id, visit)
    v = max(updated_site.visit_histories, key=lambda x: x.id or 0)
    return VisitHistorySchema(
        id=v.id,
        visit_datetime=v.visit_datetime,
        engineer_name=v.engineer_name,
        engineer_phone=v.engineer_phone,
        request_content=v.request_content,
        action_content=v.action_content,
    )


@router.put("/{site_id}/visit_histories/{visit_id}", response_model=VisitHistorySchema)
async def update_visit_history(
    site_id: int,
    visit_id: int,
    body: VisitHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    visit = next((v for v in site.visit_histories if v.id == visit_id), None)
    if not visit:
        raise HTTPException(status_code=404, detail="VisitHistory not found")
    if body.visit_datetime  is not None: visit.visit_datetime  = body.visit_datetime
    if body.engineer_name   is not None: visit.engineer_name   = body.engineer_name
    if body.engineer_phone  is not None: visit.engineer_phone  = body.engineer_phone
    if body.request_content is not None: visit.request_content = body.request_content
    if body.action_content  is not None: visit.action_content  = body.action_content
    updated_site = await use_case.update(site)
    v = next(v for v in updated_site.visit_histories if v.id == visit_id)
    return VisitHistorySchema(
        id=v.id,
        visit_datetime=v.visit_datetime,
        engineer_name=v.engineer_name,
        engineer_phone=v.engineer_phone,
        request_content=v.request_content,
        action_content=v.action_content,
    )


@router.delete("/{site_id}/visit_histories/{visit_id}", status_code=204)
async def delete_visit_history(
    site_id: int,
    visit_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    original_len = len(site.visit_histories)
    site.visit_histories = [v for v in site.visit_histories if v.id != visit_id]
    if len(site.visit_histories) == original_len:
        raise HTTPException(status_code=404, detail="VisitHistory not found")
    await use_case.update(site)
