# backend/src/application/widgets/base.py
from abc import ABC, abstractmethod

from src.domain.entities.widget import WidgetResult


class AbstractWidgetCollector(ABC):
    @abstractmethod
    async def collect(self) -> WidgetResult:
        ...
