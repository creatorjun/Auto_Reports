# backend/src/application/ports/audit_log_reader_port.py
from abc import ABC, abstractmethod

from src.domain.entities.audit_log import AuditLogPage, AuditLogQuery


class AuditLogReadError(RuntimeError):
    pass


class AuditLogReaderPort(ABC):
    @abstractmethod
    async def read(self, query: AuditLogQuery) -> AuditLogPage: ...
