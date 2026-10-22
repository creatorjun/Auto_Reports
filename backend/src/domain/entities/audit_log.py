# backend/src/domain/entities/audit_log.py
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class AuditLogEntry:
    timestamp: str
    event: str
    username: str | None
    ip: str | None
    details: dict[str, str]
    display_name: str | None = None
    email_address: str | None = None


@dataclass(frozen=True)
class AuditLogUserProfile:
    display_name: str | None = None
    email_address: str | None = None


@dataclass(frozen=True)
class AuditLogQuery:
    start_date: date | None = None
    end_date: date | None = None
    event: str = ""
    username: str = ""
    ip: str = ""
    search: str = ""
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class AuditLogPage:
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int
    events: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
