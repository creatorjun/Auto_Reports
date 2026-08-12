# backend/src/application/ports/report_analyzer_port.py
from abc import ABC, abstractmethod

from src.domain.entities.report import NewReport
from src.domain.value_objects.ai_analysis import AiAnalysis


class ReportAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, report: NewReport) -> AiAnalysis | None: ...
