# backend/src/domain/entities/sla_digest.py
from dataclasses import dataclass


@dataclass(frozen=True)
class SlaDigestEntry:
    key: str
    summary: str
    status: str
    assignee: str
    sla_id: str
    sla_name: str
    goal_millis: int
    remaining_millis: int
    paused: bool = False
    breached: bool = False
    issue_has_breached_sla: bool = False
