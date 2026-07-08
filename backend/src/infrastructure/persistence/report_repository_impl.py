# backend/src/infrastructure/persistence/report_repository_impl.py
import dataclasses
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.report import NewReport, Report
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    BreakdownWidgetData,
    CreatedVsResolvedWidgetData,
    OverdueWidgetData,
    RecentIssueWidgetData,
    ResolutionTypeWidgetData,
    SimpleIssueWidgetData,
    SlaDelayWidgetData,
    SlaMetVsViolatedWidgetData,
    SlaMonthlyWidgetData,
)
from src.domain.repositories.report_repository import ReportRepository
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.models import ReportORM

KST = ZoneInfo("Asia/Seoul")

_WIDGET_DATA_TYPE_MAP: dict[str, type] = {
    WidgetId.OVERDUE_ISSUES:         OverdueWidgetData,
    WidgetId.ISSUE_REVIEW:           SimpleIssueWidgetData,
    WidgetId.DATA_REQUEST:           SimpleIssueWidgetData,
    WidgetId.RESULT_PENDING:         SimpleIssueWidgetData,
    WidgetId.SLA_DELAY_BY_TYPE:      BreakdownWidgetData,
    WidgetId.SLA_DELAY_BY_STATUS:    BreakdownWidgetData,
    WidgetId.SLA_DELAY_REASON:       SlaDelayWidgetData,
    WidgetId.AVG_RESOLUTION_TYPE:    ResolutionTypeWidgetData,
    WidgetId.RESOLUTION_REPORT:      RecentIssueWidgetData,
    WidgetId.SLA_MET_VS_VIOLATED:    SlaMetVsViolatedWidgetData,
    WidgetId.CREATED_VS_RESOLVED:    CreatedVsResolvedWidgetData,
    WidgetId.SLA_INITIAL_RESPONSE:   SlaMonthlyWidgetData,
    WidgetId.SLA_RESOLUTION_MONTHLY: SlaMonthlyWidgetData,
}


def _serialize_widget(widget: WidgetResult) -> dict[str, Any]:
    return {
        "name":  widget.name,
        "total": widget.total,
        "jql":   widget.jql,
        "data":  dataclasses.asdict(widget.data) if widget.data is not None else None,
    }


def _deserialize_widget(widget_id: str, raw: dict[str, Any]) -> WidgetResult:
    data_type = _WIDGET_DATA_TYPE_MAP.get(widget_id)
    data = None
    if data_type is not None and raw.get("data") is not None:
        try:
            data = _dict_to_dataclass(data_type, raw["data"])
        except Exception:
            data = None
    return WidgetResult(
        name=raw.get("name", ""),
        total=raw.get("total", 0),
        jql=raw.get("jql", ""),
        data=data,
    )


def _dict_to_dataclass(cls: type, data: Any) -> Any:
    if not dataclasses.is_dataclass(cls) or not isinstance(data, dict):
        return data
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        kwargs[f.name] = _coerce_field(f.type, data.get(f.name))
    return cls(**kwargs)


def _coerce_field(type_hint: Any, value: Any) -> Any:
    import typing
    origin = getattr(type_hint, "__origin__", None)
    args   = getattr(type_hint, "__args__", ())

    if origin is list and args:
        item_type = args[0]
        if isinstance(value, list):
            return [_coerce_field(item_type, item) for item in value]
        return value if value is not None else []

    if origin is dict:
        if isinstance(value, dict) and args and len(args) == 2:
            val_type = args[1]
            if dataclasses.is_dataclass(val_type):
                return {k: _dict_to_dataclass(val_type, v) for k, v in value.items()}
        return value if value is not None else {}

    if isinstance(type_hint, type) and dataclasses.is_dataclass(type_hint) and isinstance(value, dict):
        return _dict_to_dataclass(type_hint, value)

    return value


class ReportRepositoryImpl(ReportRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, report: NewReport) -> Report:
        widgets_dict = {k: _serialize_widget(v) for k, v in report.widgets.items()}
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
        widgets = {k: _deserialize_widget(k, v) for k, v in orm.widgets.items()}
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
