# backend/src/infrastructure/persistence/site_repository_impl.py
from typing import Optional
from datetime import datetime
from enum import StrEnum

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.site import (
    AccessCredentials,
    ContactInfo,
    ContractType,
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
from src.domain.repositories.site_repository import SiteRepository
from src.infrastructure.persistence.site_models import (
    AccessCredentialsORM,
    DeploymentNodeORM,
    PatchHistoryORM,
    SiteORM,
    SolutionPackageORM,
    VisitHistoryORM,
)

_GET_ALL_LIMIT = 500


def _safe_enum(enum_cls: type[StrEnum], value):
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        for member in enum_cls:
            if member.name.lower() == str(value).lower():
                return member
        return None


class SiteRepositoryImpl(SiteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _opts(self):
        return [
            selectinload(SiteORM.nodes),
            selectinload(SiteORM.solution_package),
            selectinload(SiteORM.patch_histories),
            selectinload(SiteORM.visit_histories),
            selectinload(SiteORM.access_credentials),
        ]

    async def get_all(self) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .options(*self._opts())
            .order_by(SiteORM.site_name)
            .limit(_GET_ALL_LIMIT)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_id(self, site_id: int) -> Optional[Site]:
        result = await self._session.execute(
            select(SiteORM).where(SiteORM.id == site_id).options(*self._opts())
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_name(self, site_name: str) -> Optional[Site]:
        normalized = site_name.strip().lower()
        result = await self._session.execute(
            select(SiteORM)
            .where(func.lower(func.trim(SiteORM.site_name)) == normalized)
            .options(*self._opts())
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def save(self, site: Site) -> Site:
        if site.id is not None:
            result = await self._session.execute(
                select(SiteORM).where(SiteORM.id == site.id).options(*self._opts())
            )
            orm = result.scalar_one_or_none()
        else:
            orm = None

        if orm is None:
            existing = await self.find_by_name(site.site_name)
            if existing is not None:
                raise ValueError(f"이미 동일한 이름의 사이트가 존재합니다: '{site.site_name}'")
            orm = SiteORM()
            self._session.add(orm)

        await self._apply_domain(orm, site)
        await self._session.flush()

        refreshed = await self._session.execute(
            select(SiteORM).where(SiteORM.id == orm.id).options(*self._opts())
        )
        orm = refreshed.scalar_one()
        return self._to_domain(orm)

    async def delete(self, site_id: int) -> bool:
        result = await self._session.execute(select(SiteORM).where(SiteORM.id == site_id))
        orm = result.scalar_one_or_none()
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.flush()
        return True

    async def search(self, query: str, limit: int = 10) -> list[Site]:
        normalized = query.strip().lower()
        result = await self._session.execute(
            select(SiteORM)
            .where(func.lower(func.trim(SiteORM.site_name)).contains(normalized))
            .options(*self._opts())
            .order_by(SiteORM.site_name)
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_recent(self, limit: int = 5) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM).options(*self._opts()).order_by(SiteORM.updated_at.desc()).limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def find_by_id(self, site_id: int) -> Optional[Site]:
        return await self.get_by_id(site_id)

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM).options(*self._opts()).order_by(SiteORM.site_name).limit(limit).offset(offset)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .where(SiteORM.status == status)
            .options(*self._opts())
            .order_by(SiteORM.site_name)
            .limit(limit)
            .offset(offset)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, site: Site) -> Site:
        return await self.save(site)

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(SiteORM))
        return result.scalar_one()

    def _to_domain(self, orm: SiteORM) -> Site:
        return Site(
            id=orm.id,
            site_name=orm.site_name,
            maintenance_company=orm.maintenance_company,
            customer_contact=ContactInfo(
                name=orm.customer_name,
                phone=orm.customer_phone,
                email=orm.customer_email,
            ),
            maintenance_contact=ContactInfo(
                name=orm.maintenance_name,
                phone=orm.maintenance_phone,
                email=orm.maintenance_email,
                company=orm.maintenance_contact_company,
            ),
            contract_start_date=orm.contract_start_date,
            contract_end_date=orm.contract_end_date,
            contract_type=_safe_enum(ContractType, orm.contract_type),
            status=_safe_enum(SiteStatus, orm.status),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            nodes=[self._node_to_domain(n) for n in (orm.nodes or [])],
            solution_package=self._pkg_to_domain(orm.solution_package) if orm.solution_package else None,
            patch_histories=[self._patch_to_domain(p) for p in (orm.patch_histories or [])],
            visit_histories=[self._visit_to_domain(v) for v in (orm.visit_histories or [])],
            access_credentials=self._creds_to_domain(orm.access_credentials) if orm.access_credentials else None,
        )

    def _node_to_domain(self, orm: DeploymentNodeORM) -> DeploymentNode:
        return DeploymentNode(
            id=orm.id,
            hostname=orm.hostname,
            role=_safe_enum(NodeRole, orm.role),
            cpu_cores=orm.cpu_cores,
            cpu_threads=orm.cpu_threads,
            memory_total_gb=orm.memory_total_gb,
            disk_total_gb=orm.disk_total_gb,
            os_type=orm.os_type,
            os_version=orm.os_version,
            ip_address=orm.ip_address,
            disk_free_gb=orm.disk_free_gb,
            disk_updated_at=orm.disk_updated_at,
        )

    def _pkg_to_domain(self, orm: SolutionPackageORM) -> SolutionPackage:
        return SolutionPackage(
            id=orm.id,
            version=orm.version,
            installer_filename=orm.installer_filename,
            license_capacity_gb=orm.license_capacity_gb,
            deployment_type=_safe_enum(DeploymentType, orm.deployment_type),
            license_key=orm.license_key,
            license_expire_date=orm.license_expire_date,
            installed_at=orm.installed_at,
            updated_at=orm.updated_at,
        )

    def _patch_to_domain(self, orm: PatchHistoryORM) -> PatchHistory:
        return PatchHistory(
            id=orm.id,
            issue_link=orm.issue_link,
            patch_date=orm.patch_date,
            patch_file_link=orm.patch_file_link,
            patch_type=_safe_enum(PatchType, orm.patch_type),
            applied_by=orm.applied_by,
            result_status=_safe_enum(PatchResultStatus, orm.result_status),
            rollback_date=orm.rollback_date,
            note=orm.note,
        )

    def _visit_to_domain(self, orm: VisitHistoryORM) -> VisitHistory:
        return VisitHistory(
            id=orm.id,
            visit_datetime=orm.visit_datetime,
            engineer_name=orm.engineer_name,
            engineer_phone=orm.engineer_phone,
            request_content=orm.request_content,
            action_content=orm.action_content,
        )

    def _creds_to_domain(self, orm: AccessCredentialsORM) -> AccessCredentials:
        return AccessCredentials(
            cli=Credential(username=orm.cli_username, password=orm.cli_password, ip=orm.cli_ip, port=orm.cli_port) if orm.cli_username else None,
            web=Credential(username=orm.web_username, password=orm.web_password, ip=orm.web_ip, port=orm.web_port) if orm.web_username else None,
            db=Credential(username=orm.db_username,  password=orm.db_password,  ip=orm.db_ip,  port=orm.db_port)  if orm.db_username  else None,
            vpn=Credential(username=orm.vpn_username, password=orm.vpn_password, ip=orm.vpn_ip, port=orm.vpn_port) if orm.vpn_username else None,
            note=orm.note,
        )

    async def _apply_domain(self, orm: SiteORM, site: Site) -> None:
        orm.site_name                   = site.site_name
        orm.maintenance_company         = site.maintenance_company
        orm.customer_name               = site.customer_contact.name    if site.customer_contact    else None
        orm.customer_phone              = site.customer_contact.phone   if site.customer_contact    else None
        orm.customer_email              = site.customer_contact.email   if site.customer_contact    else None
        orm.maintenance_name            = site.maintenance_contact.name    if site.maintenance_contact else None
        orm.maintenance_phone           = site.maintenance_contact.phone   if site.maintenance_contact else None
        orm.maintenance_email           = site.maintenance_contact.email   if site.maintenance_contact else None
        orm.maintenance_contact_company = site.maintenance_contact.company if site.maintenance_contact else None
        orm.contract_start_date         = site.contract_start_date
        orm.contract_end_date           = site.contract_end_date
        orm.contract_type               = site.contract_type.value if site.contract_type else None
        orm.status                      = site.status.value if site.status else None

        incoming_node_ids = {n.id for n in site.nodes if n.id is not None}
        for n in list(orm.nodes or []):
            if n.id not in incoming_node_ids:
                await self._session.delete(n)
        for n in site.nodes:
            node_orm = next((x for x in (orm.nodes or []) if x.id == n.id), None) if n.id else None
            if node_orm is None:
                node_orm = DeploymentNodeORM(site=orm)
                if orm.nodes is None:
                    orm.nodes = []
                orm.nodes.append(node_orm)
            node_orm.hostname        = n.hostname
            node_orm.role            = n.role.value if n.role else None
            node_orm.cpu_cores       = n.cpu_cores
            node_orm.cpu_threads     = n.cpu_threads
            node_orm.memory_total_gb = n.memory_total_gb
            node_orm.disk_total_gb   = n.disk_total_gb
            node_orm.os_type         = n.os_type
            node_orm.os_version      = n.os_version
            node_orm.ip_address      = n.ip_address
            node_orm.disk_free_gb    = n.disk_free_gb
            node_orm.disk_updated_at = n.disk_updated_at

        if site.solution_package:
            pkg = orm.solution_package
            if pkg is None:
                pkg = SolutionPackageORM(site=orm)
                orm.solution_package = pkg
                self._session.add(pkg)
            pkg.version              = site.solution_package.version
            pkg.installer_filename   = site.solution_package.installer_filename
            pkg.license_capacity_gb  = site.solution_package.license_capacity_gb
            pkg.deployment_type      = site.solution_package.deployment_type.value if site.solution_package.deployment_type else None
            pkg.license_key          = site.solution_package.license_key
            pkg.license_expire_date  = site.solution_package.license_expire_date
            pkg.installed_at         = site.solution_package.installed_at
            pkg.updated_at           = site.solution_package.updated_at
        elif orm.solution_package is not None:
            await self._session.delete(orm.solution_package)
            orm.solution_package = None

        incoming_patch_ids = {p.id for p in site.patch_histories if p.id is not None}
        for p in list(orm.patch_histories or []):
            if p.id not in incoming_patch_ids:
                await self._session.delete(p)
        for p in site.patch_histories:
            patch_orm = next((x for x in (orm.patch_histories or []) if x.id == p.id), None) if p.id else None
            if patch_orm is None:
                patch_orm = PatchHistoryORM(site=orm)
                if orm.patch_histories is None:
                    orm.patch_histories = []
                orm.patch_histories.append(patch_orm)
            patch_orm.issue_link      = p.issue_link
            patch_orm.patch_date      = p.patch_date
            patch_orm.patch_file_link = p.patch_file_link
            patch_orm.patch_type      = p.patch_type.value if p.patch_type else None
            patch_orm.applied_by      = p.applied_by
            patch_orm.result_status   = p.result_status.value if p.result_status else None
            patch_orm.rollback_date   = p.rollback_date
            patch_orm.note            = p.note

        incoming_visit_ids = {v.id for v in site.visit_histories if v.id is not None}
        for v in list(orm.visit_histories or []):
            if v.id not in incoming_visit_ids:
                await self._session.delete(v)
        for v in site.visit_histories:
            visit_orm = next((x for x in (orm.visit_histories or []) if x.id == v.id), None) if v.id else None
            if visit_orm is None:
                visit_orm = VisitHistoryORM(site=orm)
                if orm.visit_histories is None:
                    orm.visit_histories = []
                orm.visit_histories.append(visit_orm)
            visit_orm.visit_datetime  = v.visit_datetime
            visit_orm.engineer_name   = v.engineer_name
            visit_orm.engineer_phone  = v.engineer_phone
            visit_orm.request_content = v.request_content
            visit_orm.action_content  = v.action_content

        if site.access_credentials:
            creds = orm.access_credentials
            if creds is None:
                creds = AccessCredentialsORM(site=orm)
                orm.access_credentials = creds
                self._session.add(creds)
            creds.cli_username = site.access_credentials.cli.username if site.access_credentials.cli else None
            creds.cli_password = site.access_credentials.cli.password if site.access_credentials.cli else None
            creds.cli_ip       = site.access_credentials.cli.ip       if site.access_credentials.cli else None
            creds.cli_port     = site.access_credentials.cli.port     if site.access_credentials.cli else None
            creds.web_username = site.access_credentials.web.username if site.access_credentials.web else None
            creds.web_password = site.access_credentials.web.password if site.access_credentials.web else None
            creds.web_ip       = site.access_credentials.web.ip       if site.access_credentials.web else None
            creds.web_port     = site.access_credentials.web.port     if site.access_credentials.web else None
            creds.db_username  = site.access_credentials.db.username  if site.access_credentials.db  else None
            creds.db_password  = site.access_credentials.db.password  if site.access_credentials.db  else None
            creds.db_ip        = site.access_credentials.db.ip        if site.access_credentials.db  else None
            creds.db_port      = site.access_credentials.db.port      if site.access_credentials.db  else None
            creds.vpn_username = site.access_credentials.vpn.username if site.access_credentials.vpn else None
            creds.vpn_password = site.access_credentials.vpn.password if site.access_credentials.vpn else None
            creds.vpn_ip       = site.access_credentials.vpn.ip       if site.access_credentials.vpn else None
            creds.vpn_port     = site.access_credentials.vpn.port     if site.access_credentials.vpn else None
            creds.note         = site.access_credentials.note
        elif orm.access_credentials is not None:
            await self._session.delete(orm.access_credentials)
            orm.access_credentials = None
