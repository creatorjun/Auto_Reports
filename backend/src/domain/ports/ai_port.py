# backend/src/domain/ports/ai_port.py
from abc import ABC, abstractmethod
from typing import Optional

from src.domain.value_objects.ai_analysis import AiAnalysis


class AiPort(ABC):
    @abstractmethod
    def analyze(self, prompt: str) -> Optional[AiAnalysis]: ...
