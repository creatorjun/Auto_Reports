# backend/src/domain/entities/sla_dashboard.py
from dataclasses import dataclass


@dataclass(frozen=True)
class SlaDashboardIssue:
    key: str
    created: str
    updated: str
    status: str


@dataclass(frozen=True)
class SlaDashboardComment:
    id: str
    author: str
    body: str
    created: str
    updated: str
