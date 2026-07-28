# backend/src/infrastructure/persistence/site_models.py
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models import Base


class SiteORM(Base):
    __tablename__ = "sites"

    id:                          Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_name:                   Mapped[str]        = mapped_column(String, nullable=False)
    maintenance_company:         Mapped[str | None] = mapped_column(String, nullable=True)
    customer_name:               Mapped[str | None] = mapped_column(String, nullable=True)
    customer_phone:              Mapped[str | None] = mapped_column(String, nullable=True)
    customer_email:              Mapped[str | None] = mapped_column(String, nullable=True)
    maintenance_name:            Mapped[str | None] = mapped_column(String, nullable=True)
    maintenance_phone:           Mapped[str | None] = mapped_column(String, nullable=True)
    maintenance_email:           Mapped[str | None] = mapped_column(String, nullable=True)
    maintenance_contact_company: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_start_date:         Mapped[date | None]     = mapped_column(Date, nullable=True)
    contract_end_date:           Mapped[date | None]     = mapped_column(Date, nullable=True)
    contract_type:               Mapped[str | None]      = mapped_column(String, nullable=True)
    status:                      Mapped[str | None]      = mapped_column(String, nullable=True)
    created_at:                  Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:                  Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    nodes:              Mapped[list["DeploymentNodeORM"]]     = relationship("DeploymentNodeORM",  back_populates="site", cascade="all, delete-orphan", lazy="selectin")
    solution_package:   Mapped["SolutionPackageORM | None"]   = relationship("SolutionPackageORM", back_populates="site", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    patch_histories:    Mapped[list["PatchHistoryORM"]]       = relationship("PatchHistoryORM",    back_populates="site", cascade="all, delete-orphan", lazy="selectin")
    visit_histories:    Mapped[list["VisitHistoryORM"]]       = relationship("VisitHistoryORM",    back_populates="site", cascade="all, delete-orphan", lazy="selectin")
    access_credentials: Mapped["AccessCredentialsORM | None"] = relationship("AccessCredentialsORM", back_populates="site", uselist=False, cascade="all, delete-orphan", lazy="selectin")


class DeploymentNodeORM(Base):
    __tablename__ = "deployment_nodes"

    id:              Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:         Mapped[int]          = mapped_column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    hostname:        Mapped[str | None]   = mapped_column(String, nullable=True)
    role:            Mapped[str | None]   = mapped_column(String, nullable=True)
    cpu_cores:       Mapped[int | None]   = mapped_column(Integer, nullable=True)
    cpu_threads:     Mapped[int | None]   = mapped_column(Integer, nullable=True)
    memory_total_gb: Mapped[int | None]   = mapped_column(Integer, nullable=True)
    disk_total_gb:   Mapped[int | None]   = mapped_column(Integer, nullable=True)
    os_type:         Mapped[str | None]   = mapped_column(String, nullable=True)
    os_version:      Mapped[str | None]   = mapped_column(String, nullable=True)
    ip_address:      Mapped[str | None]   = mapped_column(String, nullable=True)
    disk_free_gb:    Mapped[int | None]   = mapped_column(Integer, nullable=True)
    disk_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="nodes")


class SolutionPackageORM(Base):
    __tablename__ = "solution_packages"

    id:                  Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:             Mapped[int]          = mapped_column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, unique=True)
    version:             Mapped[str | None]   = mapped_column(String, nullable=True)
    installer_filename:  Mapped[str | None]   = mapped_column(String, nullable=True)
    license_capacity_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    deployment_type:     Mapped[str | None]   = mapped_column(String, nullable=True)
    license_key:         Mapped[str | None]   = mapped_column(String, nullable=True)
    license_expire_date: Mapped[date | None]  = mapped_column(Date, nullable=True)
    installed_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at:          Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="solution_package")


class PatchHistoryORM(Base):
    __tablename__ = "patch_histories"

    id:              Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:         Mapped[int]         = mapped_column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    issue_link:      Mapped[str | None]  = mapped_column(Text, nullable=True)
    patch_date:      Mapped[date | None] = mapped_column(Date, nullable=True)
    patch_file_link: Mapped[str | None]  = mapped_column(Text, nullable=True)
    patch_type:      Mapped[str | None]  = mapped_column(String, nullable=True)
    applied_by:      Mapped[str | None]  = mapped_column(String, nullable=True)
    result_status:   Mapped[str | None]  = mapped_column(String, nullable=True)
    rollback_date:   Mapped[date | None] = mapped_column(Date, nullable=True)
    note:            Mapped[str | None]  = mapped_column(Text, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="patch_histories")


class VisitHistoryORM(Base):
    __tablename__ = "visit_histories"

    id:               Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:          Mapped[int]              = mapped_column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    visit_datetime:   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    engineer_name:    Mapped[str | None]       = mapped_column(String, nullable=True)
    engineer_phone:   Mapped[str | None]       = mapped_column(String, nullable=True)
    request_content:  Mapped[str | None]       = mapped_column(Text, nullable=True)
    action_content:   Mapped[str | None]       = mapped_column(Text, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="visit_histories")


class AccessCredentialsORM(Base):
    __tablename__ = "access_credentials"

    id:           Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id:      Mapped[int]        = mapped_column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, unique=True)
    cli_username: Mapped[str | None] = mapped_column(String, nullable=True)
    cli_password: Mapped[str | None] = mapped_column(String, nullable=True)
    cli_ip:       Mapped[str | None] = mapped_column(String, nullable=True)
    cli_port:     Mapped[str | None] = mapped_column(String, nullable=True)
    web_username: Mapped[str | None] = mapped_column(String, nullable=True)
    web_password: Mapped[str | None] = mapped_column(String, nullable=True)
    web_ip:       Mapped[str | None] = mapped_column(String, nullable=True)
    web_port:     Mapped[str | None] = mapped_column(String, nullable=True)
    db_username:  Mapped[str | None] = mapped_column(String, nullable=True)
    db_password:  Mapped[str | None] = mapped_column(String, nullable=True)
    db_ip:        Mapped[str | None] = mapped_column(String, nullable=True)
    db_port:      Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_username: Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_password: Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_ip:       Mapped[str | None] = mapped_column(String, nullable=True)
    vpn_port:     Mapped[str | None] = mapped_column(String, nullable=True)
    note:         Mapped[str | None] = mapped_column(Text, nullable=True)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="access_credentials")
