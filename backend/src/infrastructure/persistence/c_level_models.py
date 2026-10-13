# backend/src/infrastructure/persistence/c_level_models.py
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models import Base


class CLevelCommentORM(Base):
    __tablename__ = "c_level_comments"

    issue_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    delay_reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    prevention_plan: Mapped[str] = mapped_column(Text, nullable=False)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CLevelSnapshotORM(Base):
    __tablename__ = "c_level_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    saved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
