# backend/src/application/widgets/base.py
from abc import ABC, abstractmethod

from src.domain.entities.widget import WidgetResult

WidgetCollection = WidgetResult | tuple[WidgetResult, WidgetResult]


class AbstractWidgetCollector(ABC):
    @abstractmethod
    async def collect(self) -> WidgetCollection:
        ...
