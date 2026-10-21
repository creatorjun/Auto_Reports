# backend/src/application/ports/sla_status_port.py
from abc import ABC, abstractmethod

from src.domain.entities.sla_violation_report import SlaViolationIssue


class SlaStatusDetailsPort(ABC):
    @abstractmethod
    async def fetch_details(self, keys: tuple[str, ...]) -> tuple[SlaViolationIssue, ...]:
        raise NotImplementedError
