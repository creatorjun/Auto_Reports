# backend/src/presentation/api/v1/sites.py
from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.use_cases.site_use_cases import SiteUseCase
from src.domain.entities.site import (
    AccessCredentials,
    ContactInfo,
    Credential,
    DeploymentNode,
    PatchHistory,
    Site,
    SolutionPackage,
    VisitHistory,
)
from src.presentation.api.v1.deps import get_site_use_case
from src.presentation.schemas.site_schema import (
    AccessCredentialsSchema,
    ContactInfoSchema,
    CredentialSchema,
    DeploymentNodeSchema,
    DeploymentNodeCreateRequest,
    DeploymentNodeUpdateRequest,
    DeploymentType,
    NodeRole,
    PatchHistorySchema,
    PatchHistoryCreateRequest,
    PatchHistoryUpdateRequest,
    SiteCreateRequest,
    SiteResponse,
    SiteSummaryResponse,
    SiteUpdateRequest,
    SolutionPackageSchema,
    SolutionPackageUpsertRequest,
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


def _pkg_to_schema(pkg: SolutionPackage | None) -> SolutionPackageSchema | None:
    if pkg is None:
        return None
    return SolutionPackageSchema(
        id=pkg.id,
        version=pkg.version,
        installer_filename=pkg.installer_filename,
        license_capacity_gb=pkg.license_capacity_gb,
        deployment_type=pkg.deployment_type.value if pkg.deployment_type else None,
        license_key=pkg.license_key,
        license_expire_date=pkg.license_expire_date,
        installed_at=pkg.installed_at,
        updated_at=pkg.updated_at,
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
                deployment_type=DeploymentType(req.solution_package.deployment_type) if req.solution_package.deployment_type else None,
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
        solution_package=_pkg_to_schema(site.solution_package),
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


@router.get("/", response_model=list[SiteSummaryResponse])
async def list_sites(
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    sites = await use_case.list_sites()
    return [
        SiteSummaryResponse(
            id=s.id,
            site_name=s.site_name,
            customer_name=s.customer_contact.name if s.customer_contact else None,
            status=s.status.value if s.status else None,
            contract_end_date=s.contract_end_date,
        )
        for s in sites
    ]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return _to_response(site)


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(
    req: SiteCreateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.create_site(_to_domain(req))
    return _to_response(site)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    req: SiteUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    site = await use_case.update_site(site_id, req.model_dump(exclude_unset=True))
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return _to_response(site)


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete_site(site_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Site not found")


@router.post("/{site_id}/nodes", response_model=DeploymentNodeSchema, status_code=201)
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
    result = await use_case.add_node(site_id, node)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return _node_to_schema(result)


@router.patch("/{site_id}/nodes/{node_id}", response_model=DeploymentNodeSchema)
async def update_node(
    site_id: int,
    node_id: int,
    req: DeploymentNodeUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    result = await use_case.update_node(site_id, node_id, req.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return _node_to_schema(result)


@router.delete("/{site_id}/nodes/{node_id}", status_code=204)
async def delete_node(
    site_id: int,
    node_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete_node(site_id, node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")


@router.put("/{site_id}/solution-package", response_model=SolutionPackageSchema)
async def upsert_solution_package(
    site_id: int,
    req: SolutionPackageUpsertRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    pkg = SolutionPackage(
        version=req.version,
        installer_filename=req.installer_filename,
        license_capacity_gb=req.license_capacity_gb,
        deployment_type=DeploymentType(req.deployment_type) if req.deployment_type else None,
        license_key=req.license_key,
        license_expire_date=req.license_expire_date,
        installed_at=req.installed_at,
    )
    result = await use_case.upsert_solution_package(site_id, pkg)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return _pkg_to_schema(result)


@router.post("/{site_id}/patch-histories", response_model=PatchHistorySchema, status_code=201)
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
    result = await use_case.add_patch_history(site_id, ph)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return PatchHistorySchema(
        id=result.id,
        issue_link=result.issue_link,
        patch_date=result.patch_date,
        patch_file_link=result.patch_file_link,
        patch_type=result.patch_type.value if result.patch_type else None,
        applied_by=result.applied_by,
        result_status=result.result_status.value if result.result_status else None,
        rollback_date=result.rollback_date,
        note=result.note,
    )


@router.patch("/{site_id}/patch-histories/{ph_id}", response_model=PatchHistorySchema)
async def update_patch_history(
    site_id: int,
    ph_id: int,
    req: PatchHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    result = await use_case.update_patch_history(site_id, ph_id, req.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail="PatchHistory not found")
    return PatchHistorySchema(
        id=result.id,
        issue_link=result.issue_link,
        patch_date=result.patch_date,
        patch_file_link=result.patch_file_link,
        patch_type=result.patch_type.value if result.patch_type else None,
        applied_by=result.applied_by,
        result_status=result.result_status.value if result.result_status else None,
        rollback_date=result.rollback_date,
        note=result.note,
    )


@router.delete("/{site_id}/patch-histories/{ph_id}", status_code=204)
async def delete_patch_history(
    site_id: int,
    ph_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete_patch_history(site_id, ph_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="PatchHistory not found")


@router.post("/{site_id}/visit-histories", response_model=VisitHistorySchema, status_code=201)
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
    result = await use_case.add_visit_history(site_id, vh)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return VisitHistorySchema(
        id=result.id,
        visit_datetime=result.visit_datetime,
        engineer_name=result.engineer_name,
        engineer_phone=result.engineer_phone,
        request_content=result.request_content,
        action_content=result.action_content,
    )


@router.patch("/{site_id}/visit-histories/{vh_id}", response_model=VisitHistorySchema)
async def update_visit_history(
    site_id: int,
    vh_id: int,
    req: VisitHistoryUpdateRequest,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    result = await use_case.update_visit_history(site_id, vh_id, req.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail="VisitHistory not found")
    return VisitHistorySchema(
        id=result.id,
        visit_datetime=result.visit_datetime,
        engineer_name=result.engineer_name,
        engineer_phone=result.engineer_phone,
        request_content=result.request_content,
        action_content=result.action_content,
    )


@router.delete("/{site_id}/visit-histories/{vh_id}", status_code=204)
async def delete_visit_history(
    site_id: int,
    vh_id: int,
    use_case: SiteUseCase = Depends(get_site_use_case),
):
    deleted = await use_case.delete_visit_history(site_id, vh_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="VisitHistory not found")
