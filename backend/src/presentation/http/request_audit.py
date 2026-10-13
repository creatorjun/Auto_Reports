# backend/src/presentation/http/request_audit.py
from fastapi import Request

from src.application.ports.audit_port import AuditPort


class RequestAudit(AuditPort):
    def __init__(self, audit: AuditPort, request: Request) -> None:
        self._audit = audit
        self._request = request

    def record(self, event: str, **fields: object) -> None:
        username = getattr(self._request.state, "authenticated_username", None)
        if username is not None:
            fields["username"] = username
        self._audit.record(event, **fields)
