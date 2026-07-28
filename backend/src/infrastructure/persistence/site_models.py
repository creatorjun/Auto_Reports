# backend/src/infrastructure/persistence/site_models.py
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models import Base


class SiteORM(Base):
    __tablename__ = "sites"

    id:                   Mapped[str]      = mapped_column(String, primary_key=True)
    site_name:            Mapped[str]      = mapped_column(String, nullable=False)
    maintenance_company:  Mapped[str]      = mapped_column(String, nullable=False)
    customer_name:        Mapped[str]      = mapped_column(String, nullable=False)
    customer_phone:       Mapped[str]      = mapped_column(String, nullable=False)
    customer_email:       Mapped[str | None] = mapped_column(String, nullable=True)
    maintenance_name:     Mapped[str]      = mapped_column(String, nullable=False)
    maintenance_phone:    Mapped[str]      = mapped_column(String, nullable=False)
    maintenance_email:    Mapped[str | None] = mapped_column(String, nullable=True)
    contract_start_date:  Mapped[date]     = mapped_column(Date, nullable=False)
    contract_end_date:    Mapped[date]     = mapped_column(Date, nullable=False)
    contract_type:        Mapped[str]      = mapped_column(String, nullable=False)
    status:               Mapped[str]      = mapped_column(String, nullable=False)
    created_at:           Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:           Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    nodes:               Mapped[list["DeploymentNodeORM"]]   = relationship("DeploymentNodeORM",  back_populates="site", cascade="all, delete-orphan")
    solution_package:    Mapped["SolutionPackageORM | None"] = relationship("SolutionPackageORM", back_populates="site", uselist=False, cascade="all, delete-orphan")
    patch_histories:     Mapped[list["PatchHistoryORM"]]     = relationship("PatchHistoryORM",    back_populates="site", cascade="all, delete-orphan")
    visit_histories:     Mapped[list["VisitHistoryORM"]]     = relationship("VisitHistoryORM",    back_populates="site", cascade="all, delete-orphan")
    access_credentials:  Mapped["AccessCredentialsORM | None"] = relationship("AccessCredentialsORM", back_populates="site", uselist=False, cascade="all, delete-orphan")


class DeploymentNodeORM(Base):
    __tablename__ = "deployment_nodes"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:         Mapped[str]      = mapped_column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    hostname:        Mapped[str]      = mapped_column(String, nullable=False)
    role:            Mapped[str]      = mapped_column(String, nullable=False)
    cpu_cores:       Mapped[int]      = mapped_column(Integer, nullable=False)
    cpu_threads:     Mapped[int]      = mapped_column(Integer, nullable=False)
    memory_total_gb: Mapped[int]      = mapped_column(Integer, nullable=False)
    disk_total_gb:   Mapped[int]      = mapped_column(Integer, nullable=False)
    os_type:         Mapped[str]      = mapped_column(String, nullable=False)
    os_version:      Mapped[str]      = mapped_column(String, nullable=False)
    ip_address:      Mapped[str | None]  = mapped_column(String, nullable=True)
    disk_free_gb:    Mapped[int | None]  = mapped_column(Integer, nullable=True)
    disk_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="nodes")


class SolutionPackageORM(Base):
    __tablename__ = "solution_packages"

    id:                  Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:             Mapped[str]      = mapped_column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, unique=True)
    version:             Mapped[str]      = mapped_column(String, nullable=False)
    installer_filename:  Mapped[str]      = mapped_column(String, nullable=False)
    license_capacity_gb: Mapped[float]    = mapped_column(Float, nullable=False)
    deployment_type:     Mapped[str]      = mapped_column(String, nullable=False)
    license_key:         Mapped[str | None]  = mapped_column(String, nullable=True)
    license_expire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    installed_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at:          Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="solution_package")


class PatchHistoryORM(Base):
    __tablename__ = "patch_histories"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:         Mapped[str]      = mapped_column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    issue_link:      Mapped[str]      = mapped_column(Text, nullable=False)
    patch_date:      Mapped[date]     = mapped_column(Date, nullable=False)
    patch_file_link: Mapped[str]      = mapped_column(Text, nullable=False)
    patch_type:      Mapped[str]      = mapped_column(String, nullable=False)
    applied_by:      Mapped[str]      = mapped_column(String, nullable=False, default="")
    result_status:   Mapped[str]      = mapped_column(String, nullable=False)
    rollback_date:   Mapped[date | None] = mapped_column(Date, nullable=True)
    note:            Mapped[str | None]  = mapped_column(Text, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="patch_histories")


class VisitHistoryORM(Base):
    __tablename__ = "visit_histories"

    id:                   Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:              Mapped[str]       = mapped_column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    visit_date:           Mapped[date]      = mapped_column(Date, nullable=False)
    visitor:              Mapped[str]       = mapped_column(String, nullable=False)
    visit_type:           Mapped[str]       = mapped_column(String, nullable=False)
    visit_summary:        Mapped[str]       = mapped_column(Text, nullable=False)
    next_visit_scheduled: Mapped[date | None] = mapped_column(Date, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="visit_histories")


class AccessCredentialsORM(Base):
    __tablename__ = "access_credentials"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:      Mapped[str]      = mapped_column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, unique=True)
    cli_username: Mapped[str | None] = mapped_column(String, nullable=True)
    cli_password: Mapped[str | None] = mapped_column(String, nullable=True)
    web_username: Mapped[str | None] = mapped_column(String, nullable=True)
    web_password: Mapped[str | None] = mapped_column(String, nullable=True)
    db_username:  Mapped[str | None] = mapped_column(String, nullable=True)
    db_password:  Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_username: Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_password: Mapped[str | None] = mapped_column(String, nullable=True)
    note:         Mapped[str | None] = mapped_column(Text, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="access_credentials")
