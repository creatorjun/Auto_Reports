# backend/src/infrastructure/persistence/sla_violation_models.py
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models import Base


class SlaViolationReportORM(Base):
    __tablename__ = "sla_violation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    selected_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    ticket_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_response_count: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)

    __table_args__ = (
        Index("ix_sla_violation_reports_generated_at_id", "generated_at", "id"),
    )
