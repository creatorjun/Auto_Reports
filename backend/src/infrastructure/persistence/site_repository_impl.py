# backend/src/infrastructure/persistence/site_repository_impl.py
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from src.domain.repositories.site_repository import SiteRepository
from src.infrastructure.persistence.site_models import (
    DeploymentNodeORM,
    PatchHistoryORM,
    SiteORM,
    SolutionPackageORM,
    VisitHistoryORM,
)


class SiteRepositoryImpl(SiteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, site: Site) -> Site:
        orm = self._to_orm(site)
        self._session.add(orm)
        await self._session.flush()
        return self._to_entity(orm)

    async def find_by_id(self, site_id: str) -> Optional[Site]:
        stmt = (
            select(SiteORM)
            .where(SiteORM.id == site_id)
            .options(
                selectinload(SiteORM.nodes),
                selectinload(SiteORM.solution_package),
                selectinload(SiteORM.patch_histories),
                selectinload(SiteORM.visit_histories),
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]:
        stmt = (
            select(SiteORM)
            .options(
                selectinload(SiteORM.nodes),
                selectinload(SiteORM.solution_package),
                selectinload(SiteORM.patch_histories),
                selectinload(SiteORM.visit_histories),
            )
            .order_by(SiteORM.site_name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def find_by_status(self, status: str, limit: int = 20, offset: int = 0) -> list[Site]:
        stmt = (
            select(SiteORM)
            .where(SiteORM.status == status)
            .options(
                selectinload(SiteORM.nodes),
                selectinload(SiteORM.solution_package),
                selectinload(SiteORM.patch_histories),
                selectinload(SiteORM.visit_histories),
            )
            .order_by(SiteORM.site_name)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update(self, site: Site) -> Site:
        existing = await self._session.get(SiteORM, site.id)
        if not existing:
            return await self.save(site)
        self._apply_to_orm(existing, site)
        await self._session.flush()
        return site

    async def delete(self, site_id: str) -> bool:
        existing = await self._session.get(SiteORM, site_id)
        if not existing:
            return False
        await self._session.delete(existing)
        await self._session.flush()
        return True

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(SiteORM))
        return result.scalar_one()

    def _to_orm(self, site: Site) -> SiteORM:
        orm = SiteORM(
            id=site.id,
            site_name=site.site_name,
            maintenance_company=site.maintenance_company,
            customer_name=site.customer_contact.name,
            customer_phone=site.customer_contact.phone,
            customer_email=site.customer_contact.email,
            maintenance_name=site.maintenance_contact.name,
            maintenance_phone=site.maintenance_contact.phone,
            maintenance_email=site.maintenance_contact.email,
            contract_start_date=site.contract_start_date,
            contract_end_date=site.contract_end_date,
            contract_type=site.contract_type.value,
            status=site.status.value,
        )
        orm.nodes = [
            DeploymentNodeORM(
                site_id=site.id,
                hostname=n.hostname,
                role=n.role.value,
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
            for n in site.nodes
        ]
        if site.solution_package:
            pkg = site.solution_package
            orm.solution_package = SolutionPackageORM(
                site_id=site.id,
                version=pkg.version,
                installer_filename=pkg.installer_filename,
                license_capacity_gb=pkg.license_capacity_gb,
                deployment_type=pkg.deployment_type.value,
                license_key=pkg.license_key,
                license_expire_date=pkg.license_expire_date,
                installed_at=pkg.installed_at,
                updated_at=pkg.updated_at,
            )
        orm.patch_histories = [
            PatchHistoryORM(
                site_id=site.id,
                issue_link=p.issue_link,
                patch_date=p.patch_date,
                patch_file_link=p.patch_file_link,
                patch_type=p.patch_type.value,
                applied_by=p.applied_by,
                result_status=p.result_status.value,
                rollback_date=p.rollback_date,
                note=p.note,
            )
            for p in site.patch_histories
        ]
        orm.visit_histories = [
            VisitHistoryORM(
                site_id=site.id,
                visit_date=v.visit_date,
                visitor=v.visitor,
                visit_type=v.visit_type.value,
                visit_summary=v.visit_summary,
                next_visit_scheduled=v.next_visit_scheduled,
            )
            for v in site.visit_histories
        ]
        return orm

    def _apply_to_orm(self, orm: SiteORM, site: Site) -> None:
        orm.site_name           = site.site_name
        orm.maintenance_company = site.maintenance_company
        orm.customer_name       = site.customer_contact.name
        orm.customer_phone      = site.customer_contact.phone
        orm.customer_email      = site.customer_contact.email
        orm.maintenance_name    = site.maintenance_contact.name
        orm.maintenance_phone   = site.maintenance_contact.phone
        orm.maintenance_email   = site.maintenance_contact.email
        orm.contract_start_date = site.contract_start_date
        orm.contract_end_date   = site.contract_end_date
        orm.contract_type       = site.contract_type.value
        orm.status              = site.status.value

    @staticmethod
    def _to_entity(orm: SiteORM) -> Site:
        nodes = [
            DeploymentNode(
                hostname=n.hostname,
                role=NodeRole(n.role),
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
            for n in (orm.nodes or [])
        ]
        pkg = None
        if orm.solution_package:
            p = orm.solution_package
            pkg = SolutionPackage(
                version=p.version,
                installer_filename=p.installer_filename,
                license_capacity_gb=p.license_capacity_gb,
                deployment_type=DeploymentType(p.deployment_type),
                license_key=p.license_key,
                license_expire_date=p.license_expire_date,
                installed_at=p.installed_at,
                updated_at=p.updated_at,
            )
        patches = [
            PatchHistory(
                issue_link=p.issue_link,
                patch_date=p.patch_date,
                patch_file_link=p.patch_file_link,
                patch_type=PatchType(p.patch_type),
                applied_by=p.applied_by,
                result_status=PatchResultStatus(p.result_status),
                rollback_date=p.rollback_date,
                note=p.note,
            )
            for p in (orm.patch_histories or [])
        ]
        visits = [
            VisitHistory(
                visit_date=v.visit_date,
                visitor=v.visitor,
                visit_type=VisitType(v.visit_type),
                visit_summary=v.visit_summary,
                next_visit_scheduled=v.next_visit_scheduled,
            )
            for v in (orm.visit_histories or [])
        ]
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
            contract_type=ContractType(orm.contract_type),
            status=SiteStatus(orm.status),
            nodes=nodes,
            solution_package=pkg,
            patch_histories=patches,
            visit_histories=visits,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
