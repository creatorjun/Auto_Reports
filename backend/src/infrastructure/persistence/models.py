# backend/src/infrastructure/persistence/models.py
from datetime import datetime
from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReportORM(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    week_end: Mapped[datetime] = mapped_column(Date, nullable=False)
    report_date: Mapped[str] = mapped_column(String, nullable=False)
    widgets: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
