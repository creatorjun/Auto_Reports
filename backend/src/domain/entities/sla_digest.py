# backend/src/domain/entities/sla_digest.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


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


@dataclass(frozen=True)
class SlaDigestResult:
    status: Literal["sent", "no_matches", "already_sent", "preview"]
    ticket_count: int
    sla_count: int
    recipient_count: int
    generated_at: datetime
