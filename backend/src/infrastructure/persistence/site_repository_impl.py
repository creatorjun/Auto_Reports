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

    async def get_all(self) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM).options(
                selectinload(SiteORM.nodes),
                selectinload(SiteORM.solution_package),
                selectinload(SiteORM.patch_histories),
                selectinload(SiteORM.visit_histories),
            )
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_id(self, site_id: str) -> Optional[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .where(SiteORM.id == site_id)
            .options(
                selectinload(SiteORM.nodes),
                selectinload(SiteORM.solution_package),
                selectinload(SiteORM.patch_histories),
                selectinload(SiteORM.visit_histories),
            )
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def save(self, site: Site) -> Site:
        result = await self._session.execute(
            select(SiteORM).where(SiteORM.id == site.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = SiteORM(id=site.id)
            self._session.add(orm)
        self._apply_domain(orm, site)
        await self._session.flush()
        await self._session.refresh(
            orm,
            attribute_names=["nodes", "solution_package", "patch_histories", "visit_histories"],
        )
        return self._to_domain(orm)

    async def delete(self, site_id: str) -> bool:
        result = await self._session.execute(
            select(SiteORM).where(SiteORM.id == site_id)
        )
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
            select(SiteORM)
            .order_by(SiteORM.updated_at.desc())
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def find_by_id(self, site_id: str) -> Optional[Site]:
        return await self.get_by_id(site_id)

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Site]:
        result = await self._session.execute(
            select(SiteORM)
            .order_by(SiteORM.site_name)
            .limit(limit)
            .offset(offset)
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
            customer_info=ContactInfo(name=orm.customer_name, phone=orm.customer_phone, email=orm.customer_email),
            maintenance_info=ContactInfo(name=orm.maintenance_name, phone=orm.maintenance_phone, email=orm.maintenance_email),
            contract_start_date=orm.contract_start_date,
            contract_end_date=orm.contract_end_date,
            contract_type=ContractType(orm.contract_type),
            status=SiteStatus(orm.status),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            nodes=[self._node_to_domain(n) for n in (orm.nodes or [])],
            solution_package=self._pkg_to_domain(orm.solution_package) if orm.solution_package else None,
            patch_histories=[self._patch_to_domain(p) for p in (orm.patch_histories or [])],
            visit_histories=[self._visit_to_domain(v) for v in (orm.visit_histories or [])],
        )

    def _node_to_domain(self, orm: DeploymentNodeORM) -> DeploymentNode:
        return DeploymentNode(
            id=orm.id,
            site_id=orm.site_id,
            hostname=orm.hostname,
            role=NodeRole(orm.role),
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
            site_id=orm.site_id,
            version=orm.version,
            installer_filename=orm.installer_filename,
            license_capacity_gb=orm.license_capacity_gb,
            deployment_type=DeploymentType(orm.deployment_type),
            license_key=orm.license_key,
            license_expire_date=orm.license_expire_date,
            installed_at=orm.installed_at,
            updated_at=orm.updated_at,
        )

    def _patch_to_domain(self, orm: PatchHistoryORM) -> PatchHistory:
        return PatchHistory(
            id=orm.id,
            site_id=orm.site_id,
            issue_link=orm.issue_link,
            patch_date=orm.patch_date,
            patch_file_link=orm.patch_file_link,
            patch_type=PatchType(orm.patch_type),
            applied_by=orm.applied_by,
            result_status=PatchResultStatus(orm.result_status),
            rollback_date=orm.rollback_date,
            note=orm.note,
        )

    def _visit_to_domain(self, orm: VisitHistoryORM) -> VisitHistory:
        return VisitHistory(
            id=orm.id,
            site_id=orm.site_id,
            visit_date=orm.visit_date,
            visitor=orm.visitor,
            visit_type=VisitType(orm.visit_type),
            visit_summary=orm.visit_summary,
            next_visit_scheduled=orm.next_visit_scheduled,
        )

    def _apply_domain(self, orm: SiteORM, site: Site) -> None:
        orm.site_name = site.site_name
        orm.maintenance_company = site.maintenance_company
        orm.customer_name = site.customer_info.name
        orm.customer_phone = site.customer_info.phone
        orm.customer_email = site.customer_info.email
        orm.maintenance_name = site.maintenance_info.name
        orm.maintenance_phone = site.maintenance_info.phone
        orm.maintenance_email = site.maintenance_info.email
        orm.contract_start_date = site.contract_start_date
        orm.contract_end_date = site.contract_end_date
        orm.contract_type = site.contract_type.value
        orm.status = site.status.value
