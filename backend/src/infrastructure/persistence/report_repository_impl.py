# backend/src/infrastructure/persistence/report_repository_impl.py
import dataclasses
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.report import NewReport, Report
from src.domain.repositories.report_repository import ReportRepository
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.infrastructure.persistence.models import ReportORM
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget

KST = ZoneInfo("Asia/Seoul")


class ReportRepositoryImpl(ReportRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, report: NewReport) -> Report:
        widgets_dict = {k: serialize_widget(v) for k, v in report.widgets.items()}
        ai_dict = dataclasses.asdict(report.ai_analysis) if report.ai_analysis else None
        orm = ReportORM(
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            widgets=widgets_dict,
            ai_analysis=ai_dict,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return Report(
            id=orm.id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            widgets=report.widgets,
            ai_analysis=report.ai_analysis,
            created_at=self._to_kst(orm.created_at),
        )

    async def find_by_id(self, report_id: int) -> Optional[Report]:
        result = await self._session.execute(
            select(ReportORM).where(ReportORM.id == report_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def find_latest(self) -> Optional[Report]:
        result = await self._session.execute(
            select(ReportORM).order_by(desc(ReportORM.created_at)).limit(1)
        )
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        result = await self._session.execute(
            select(ReportORM).order_by(desc(ReportORM.created_at)).limit(limit).offset(offset)
        )
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def delete(self, report_id: int) -> bool:
        result = await self._session.execute(
            delete(ReportORM).where(ReportORM.id == report_id)
        )
        await self._session.commit()
        return result.rowcount > 0

    @staticmethod
    def _to_kst(dt: datetime) -> datetime:
        if dt is None:
            return dt
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST)

    @staticmethod
    def _to_entity(orm: ReportORM) -> Report:
        widgets = {k: deserialize_widget(k, v) for k, v in orm.widgets.items()}
        ai = AiAnalysis(**orm.ai_analysis) if orm.ai_analysis else None
        return Report(
            id=orm.id,
            week_start=orm.week_start,
            week_end=orm.week_end,
            report_date=orm.report_date,
            widgets=widgets,
            ai_analysis=ai,
            created_at=ReportRepositoryImpl._to_kst(orm.created_at),
        )
