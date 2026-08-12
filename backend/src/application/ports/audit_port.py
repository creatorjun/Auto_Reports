# backend/src/application/ports/audit_port.py
from abc import ABC, abstractmethod


class AuditPort(ABC):
    @abstractmethod
    def record(self, event: str, **fields: object) -> None: ...
