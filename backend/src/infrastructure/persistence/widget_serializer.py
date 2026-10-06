# backend/src/infrastructure/persistence/widget_serializer.py
import dataclasses
import types
from functools import lru_cache
from typing import Any, get_args, get_origin

from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    CreatedVsResolvedWidgetData,
    MonthlyCountWidgetData,
    RedeploymentAnalyticsWidgetData,
    RecentIssueWidgetData,
    ResolutionTypeWidgetData,
    SimpleIssueWidgetData,
    SlaDelayWidgetData,
    SlaMetVsViolatedWidgetData,
    SlaMonthlyWidgetData,
    TypeCountWidgetData,
)
from src.domain.value_objects.widget_id import WidgetId

_WIDGET_DATA_TYPE_MAP: dict[str, type] = {
    WidgetId.YEARLY_CREATED:         TypeCountWidgetData,
    WidgetId.YEARLY_RESOLVED:        TypeCountWidgetData,
    WidgetId.CREATED_VS_RESOLVED:    CreatedVsResolvedWidgetData,
    WidgetId.ISSUE_REVIEW:           SimpleIssueWidgetData,
    WidgetId.DATA_REQUEST:           SimpleIssueWidgetData,
    WidgetId.RESULT_PENDING:         SimpleIssueWidgetData,
    WidgetId.RECENT_ISSUES:          RecentIssueWidgetData,
    WidgetId.MONTHLY_CREATED:        MonthlyCountWidgetData,
    WidgetId.MONTHLY_RESOLVED:       MonthlyCountWidgetData,
    WidgetId.SLA_INITIAL_RESPONSE:   SlaMonthlyWidgetData,
    WidgetId.SLA_RESOLUTION_MONTHLY: SlaMonthlyWidgetData,
    WidgetId.SLA_MET_VS_VIOLATED:    SlaMetVsViolatedWidgetData,
    WidgetId.SLA_DELAY_REASON:       SlaDelayWidgetData,
    WidgetId.AVG_RESOLUTION_TYPE:    ResolutionTypeWidgetData,
    WidgetId.REDEPLOYMENT_ANALYTICS: RedeploymentAnalyticsWidgetData,
}


def serialize_widget(widget: WidgetResult) -> dict[str, Any]:
    return {
        "name":  widget.name,
        "total": widget.total,
        "jql":   widget.jql,
        "data":  dataclasses.asdict(widget.data) if widget.data is not None else None,
    }


def deserialize_widget(widget_id: str, raw: dict[str, Any]) -> WidgetResult:
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


@lru_cache(maxsize=128)
def _dataclass_fields(cls: type) -> tuple[dataclasses.Field, ...]:
    return dataclasses.fields(cls)


@lru_cache(maxsize=256)
def _field_metadata(type_hint: Any) -> tuple[Any, tuple[Any, ...], bool]:
    return (
        get_origin(type_hint),
        get_args(type_hint),
        isinstance(type_hint, type) and dataclasses.is_dataclass(type_hint),
    )


def _dict_to_dataclass(cls: type, data: Any) -> Any:
    if not dataclasses.is_dataclass(cls) or not isinstance(data, dict):
        return data
    kwargs: dict[str, Any] = {}
    for f in _dataclass_fields(cls):
        if f.name not in data:
            continue
        kwargs[f.name] = _coerce_field(f.type, data.get(f.name))
    return cls(**kwargs)


def _coerce_field(type_hint: Any, value: Any) -> Any:
    origin, args, is_dataclass = _field_metadata(type_hint)

    if origin is list and args:
        item_type = args[0]
        if isinstance(value, list):
            return [_coerce_field(item_type, item) for item in value]
        return value if value is not None else []

    if origin is dict:
        if isinstance(value, dict) and args and len(args) == 2:
            val_type = args[1]
            return {k: _coerce_field(val_type, item) for k, item in value.items()}
        return value if value is not None else {}

    if origin is types.UnionType:
        if value is None:
            return None
        candidate = next((arg for arg in args if arg is not type(None)), None)
        return _coerce_field(candidate, value)

    if is_dataclass and isinstance(value, dict):
        return _dict_to_dataclass(type_hint, value)

    return value
