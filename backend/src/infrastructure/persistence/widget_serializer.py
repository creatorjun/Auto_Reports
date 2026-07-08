# backend/src/infrastructure/persistence/widget_serializer.py
"""WidgetResult 직렬화/역직렬화 전담 모듈."""
import dataclasses
from typing import Any

from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    CreatedVsResolvedWidgetData,
    OverdueWidgetData,
    RecentIssueWidgetData,
    ResolutionTypeWidgetData,
    SimpleIssueWidgetData,
    SlaDelayWidgetData,
    SlaMetVsViolatedWidgetData,
    SlaMonthlyWidgetData,
)
from src.domain.value_objects.widget_id import WidgetId

_WIDGET_DATA_TYPE_MAP: dict[str, type] = {
    WidgetId.YEARLY_CREATED:         None,
    WidgetId.YEARLY_RESOLVED:        None,
    WidgetId.CREATED_VS_RESOLVED:    CreatedVsResolvedWidgetData,
    WidgetId.ISSUE_REVIEW:           SimpleIssueWidgetData,
    WidgetId.DATA_REQUEST:           SimpleIssueWidgetData,
    WidgetId.RESULT_PENDING:         SimpleIssueWidgetData,
    WidgetId.SLA_INITIAL_RESPONSE:   SlaMonthlyWidgetData,
    WidgetId.SLA_RESOLUTION_MONTHLY: SlaMonthlyWidgetData,
    WidgetId.SLA_MET_VS_VIOLATED:    SlaMetVsViolatedWidgetData,
    WidgetId.SLA_DELAY_REASON:       SlaDelayWidgetData,
    WidgetId.AVG_RESOLUTION_TYPE:    ResolutionTypeWidgetData,
    WidgetId.OVERDUE_ISSUES:         OverdueWidgetData,
    WidgetId.RECENT_ISSUES:          RecentIssueWidgetData,
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


def _dict_to_dataclass(cls: type, data: Any) -> Any:
    if not dataclasses.is_dataclass(cls) or not isinstance(data, dict):
        return data
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(cls):
        kwargs[f.name] = _coerce_field(f.type, data.get(f.name))
    return cls(**kwargs)


def _coerce_field(type_hint: Any, value: Any) -> Any:
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
