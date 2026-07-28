# backend/src/infrastructure/persistence/site_repository_impl.py
from typing import Optional
from datetime import datetime

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
    VisitType,
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
        result = await self._session.execute(select(SiteORM).options(*self._opts()))
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_id(self, site_id: str) -> Optional[Site]:
        result = await self._session.execute(
            select(SiteORM).where(SiteORM.id == site_id).options(*self._opts())
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def save(self, site: Site) -> Site:
        result = await self._session.execute(select(SiteORM).where(SiteORM.id == site.id))
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = SiteORM(id=site.id)
            self._session.add(orm)
        self._apply_domain(orm, site)
        await self._session.flush()
        await self._session.refresh(
            orm,
            attribute_names=["nodes", "solution_package", "patch_histories", "visit_histories", "access_credentials"],
        )
        return self._to_domain(orm)

    async def delete(self, site_id: str) -> bool:
        result = await self._session.execute(select(SiteORM).where(SiteORM.id == site_id))
        orm = result.scalar_one_or_none()
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.flush()
        return True

    async def search(self, query: str, limit: int = 10) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .where(SiteORM.site_name.ilike(f"%{query}%"))
            .order_by(SiteORM.site_name)
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_recent(self, limit: int = 5) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM).order_by(SiteORM.updated_at.desc()).limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def find_by_id(self, site_id: str) -> Optional[Site]:
        return await self.get_by_id(site_id)

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM).order_by(SiteORM.site_name).limit(limit).offset(offset)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .where(SiteORM.status == status)
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
            ),
            contract_start_date=orm.contract_start_date,
            contract_end_date=orm.contract_end_date,
            contract_type=ContractType(orm.contract_type) if orm.contract_type else None,
            status=SiteStatus(orm.status) if orm.status else None,
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
            hostname=orm.hostname,
            role=NodeRole(orm.role) if orm.role else None,
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
            version=orm.version,
            installer_filename=orm.installer_filename,
            license_capacity_gb=orm.license_capacity_gb,
            deployment_type=DeploymentType(orm.deployment_type) if orm.deployment_type else None,
            license_key=orm.license_key,
            license_expire_date=orm.license_expire_date,
            installed_at=orm.installed_at,
            updated_at=orm.updated_at,
        )

    def _patch_to_domain(self, orm: PatchHistoryORM) -> PatchHistory:
        return PatchHistory(
            issue_link=orm.issue_link,
            patch_date=orm.patch_date,
            patch_file_link=orm.patch_file_link,
            patch_type=PatchType(orm.patch_type) if orm.patch_type else None,
            applied_by=orm.applied_by,
            result_status=PatchResultStatus(orm.result_status) if orm.result_status else None,
            rollback_date=orm.rollback_date,
            note=orm.note,
        )

    def _visit_to_domain(self, orm: VisitHistoryORM) -> VisitHistory:
        return VisitHistory(
            visit_date=orm.visit_date,
            visitor=orm.visitor,
            visit_type=VisitType(orm.visit_type) if orm.visit_type else None,
            visit_summary=orm.visit_summary,
            next_visit_scheduled=orm.next_visit_scheduled,
        )

    def _creds_to_domain(self, orm: AccessCredentialsORM) -> AccessCredentials:
        return AccessCredentials(
            cli=Credential(username=orm.cli_username, password=orm.cli_password)
                if orm.cli_username is not None else None,
            web=Credential(username=orm.web_username, password=orm.web_password)
                if orm.web_username is not None else None,
            db=Credential(username=orm.db_username, password=orm.db_password)
                if orm.db_username is not None else None,
            vpn=Credential(username=orm.vpn_username, password=orm.vpn_password)
                if orm.vpn_username is not None else None,
            note=orm.note,
        )

    def _apply_domain(self, orm: SiteORM, site: Site) -> None:
        orm.site_name            = site.site_name
        orm.maintenance_company  = site.maintenance_company
        orm.customer_name        = site.customer_contact.name  if site.customer_contact  else None
        orm.customer_phone       = site.customer_contact.phone if site.customer_contact  else None
        orm.customer_email       = site.customer_contact.email if site.customer_contact  else None
        orm.maintenance_name     = site.maintenance_contact.name  if site.maintenance_contact else None
        orm.maintenance_phone    = site.maintenance_contact.phone if site.maintenance_contact else None
        orm.maintenance_email    = site.maintenance_contact.email if site.maintenance_contact else None
        orm.contract_start_date  = site.contract_start_date
        orm.contract_end_date    = site.contract_end_date
        orm.contract_type        = site.contract_type.value if site.contract_type else None
        orm.status               = site.status.value       if site.status       else None

        if site.access_credentials is not None:
            if orm.access_credentials is None:
                creds_orm = AccessCredentialsORM(site_id=site.id)
                self._session.add(creds_orm)
                orm.access_credentials = creds_orm
            self._apply_credentials(orm.access_credentials, site.access_credentials)
        else:
            orm.access_credentials = None

    def _apply_credentials(self, orm: AccessCredentialsORM, creds: AccessCredentials) -> None:
        orm.cli_username = creds.cli.username if creds.cli else None
        orm.cli_password = creds.cli.password if creds.cli else None
        orm.web_username = creds.web.username if creds.web else None
        orm.web_password = creds.web.password if creds.web else None
        orm.db_username  = creds.db.username  if creds.db  else None
        orm.db_password  = creds.db.password  if creds.db  else None
        orm.vpn_username = creds.vpn.username if creds.vpn else None
        orm.vpn_password = creds.vpn.password if creds.vpn else None
        orm.note         = creds.note
