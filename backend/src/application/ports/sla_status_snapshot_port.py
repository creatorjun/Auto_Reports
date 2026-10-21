# backend/src/application/ports/sla_status_snapshot_port.py
from abc import ABC, abstractmethod

from src.domain.entities.sla_status import SlaStatusSnapshot


class SlaStatusSnapshotPort(ABC):
    @abstractmethod
    async def load(self, project_key: str) -> SlaStatusSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, project_key: str, snapshot: SlaStatusSnapshot) -> SlaStatusSnapshot:
        raise NotImplementedError
