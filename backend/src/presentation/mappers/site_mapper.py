# backend/src/presentation/mappers/site_mapper.py
from src.domain.entities.site import (
    AccessCredentials,
    ContactInfo,
    Credential,
    DeploymentNode,
    PatchHistory,
    Site,
    SiteSummary,
    VisitHistory,
)
from src.presentation.schemas.site_schema import (
    AccessCredentialsSchema,
    ContactInfoSchema,
    CredentialSchema,
    DeploymentNodeSchema,
    PatchHistorySchema,
    SiteResponse,
    SiteSummaryResponse,
    VisitHistorySchema,
)


def creds_from_schema(schema: AccessCredentialsSchema | None) -> AccessCredentials | None:
    if schema is None:
        return None
    return AccessCredentials(
        cli=Credential(username=schema.cli.username, password=schema.cli.password, ip=schema.cli.ip, port=schema.cli.port) if schema.cli else None,
        web=Credential(username=schema.web.username, password=schema.web.password, ip=schema.web.ip, port=schema.web.port) if schema.web else None,
        db=Credential(username=schema.db.username, password=schema.db.password, ip=schema.db.ip, port=schema.db.port) if schema.db else None,
        vpn=Credential(username=schema.vpn.username, password=schema.vpn.password, ip=schema.vpn.ip, port=schema.vpn.port) if schema.vpn else None,
        note=schema.note,
    )


def creds_to_schema(creds: AccessCredentials | None) -> AccessCredentialsSchema | None:
    if creds is None:
        return None
    return AccessCredentialsSchema(
        cli=CredentialSchema(username=creds.cli.username, password=creds.cli.password, ip=creds.cli.ip, port=creds.cli.port) if creds.cli else None,
        web=CredentialSchema(username=creds.web.username, password=creds.web.password, ip=creds.web.ip, port=creds.web.port) if creds.web else None,
        db=CredentialSchema(username=creds.db.username, password=creds.db.password, ip=creds.db.ip, port=creds.db.port) if creds.db else None,
        vpn=CredentialSchema(username=creds.vpn.username, password=creds.vpn.password, ip=creds.vpn.ip, port=creds.vpn.port) if creds.vpn else None,
        note=creds.note,
    )


def contact_from_schema(s: ContactInfoSchema | None) -> ContactInfo | None:
    if s is None:
        return None
    return ContactInfo(name=s.name, phone=s.phone, email=s.email, company=s.company)


def contact_to_schema(c: ContactInfo | None) -> ContactInfoSchema | None:
    if c is None:
        return None
    return ContactInfoSchema(name=c.name, phone=c.phone, email=c.email, company=c.company)


def node_to_schema(n: DeploymentNode) -> DeploymentNodeSchema:
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
        pkg_version=n.pkg_version,
    )


def patch_to_schema(p: PatchHistory) -> PatchHistorySchema:
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


def visit_to_schema(v: VisitHistory) -> VisitHistorySchema:
    return VisitHistorySchema(
        id=v.id,
        visit_datetime=v.visit_datetime,
        engineer_name=v.engineer_name,
        engineer_phone=v.engineer_phone,
        request_content=v.request_content,
        action_content=v.action_content,
    )


def site_to_response(site: Site) -> SiteResponse:
    return SiteResponse(
        id=site.id,
        site_name=site.site_name,
        maintenance_company=site.maintenance_company,
        customer_info=contact_to_schema(site.customer_contact),
        maintenance_info=contact_to_schema(site.maintenance_contact),
        contract_start_date=site.contract_start_date,
        contract_end_date=site.contract_end_date,
        contract_type=site.contract_type.value if site.contract_type else None,
        status=site.status.value if site.status else None,
        created_at=site.created_at,
        updated_at=site.updated_at,
        nodes=[node_to_schema(n) for n in site.nodes],
        patch_histories=[patch_to_schema(p) for p in site.patch_histories],
        visit_histories=[visit_to_schema(v) for v in site.visit_histories],
        access_credentials=creds_to_schema(site.access_credentials),
    )


def site_to_summary(site: SiteSummary) -> SiteSummaryResponse:
    return SiteSummaryResponse(
        id=site.id,
        site_name=site.site_name,
        customer_name=site.customer_name,
        status=site.status.value if site.status else None,
        contract_end_date=site.contract_end_date,
    )
