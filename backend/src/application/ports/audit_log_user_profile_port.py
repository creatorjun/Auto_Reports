# backend/src/application/ports/audit_log_user_profile_port.py
from abc import ABC, abstractmethod

from src.domain.entities.audit_log import AuditLogUserProfile


class AuditLogUserProfilePort(ABC):
    @abstractmethod
    async def read_profiles(self) -> dict[str, AuditLogUserProfile]:
        raise NotImplementedError
