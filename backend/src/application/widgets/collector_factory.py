# backend/src/application/widgets/collector_factory.py
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.application.services.query_builder import BuiltQuery, WidgetQueryBuilder
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.value_objects.widget_id import WidgetId


@dataclass(frozen=True)
class CollectorEntry:
    widget_id: WidgetId
    collector: AbstractWidgetCollector


BaseCollectorFactory = Callable[[BuiltQuery, datetime], list[CollectorEntry]]
MonthlyCollectorFactory = Callable[[BuiltQuery, datetime], list[tuple[WidgetId, object]]]
