# backend/src/application/ports/audit_log_reader_port.py
from abc import ABC, abstractmethod
from collections.abc import Mapping

from src.domain.entities.audit_log import AuditLogPage, AuditLogQuery, AuditLogUserProfile


class AuditLogReadError(RuntimeError):
    pass


class AuditLogReaderPort(ABC):
    @abstractmethod
    async def read(self, query: AuditLogQuery, profiles: Mapping[str, AuditLogUserProfile] | None = None) -> AuditLogPage:
        raise NotImplementedError
