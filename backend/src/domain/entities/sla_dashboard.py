# backend/src/domain/entities/sla_dashboard.py
from dataclasses import dataclass


@dataclass(frozen=True)
class SlaDashboardIssue:
    key: str
    type: str
    summary: str
    created: str
    updated: str
    status: str


@dataclass(frozen=True)
class SlaDashboardCommentImage:
    attachment_id: str
    alt: str


@dataclass(frozen=True)
class SlaDashboardComment:
    id: str
    author: str
    body: str
    created: str
    updated: str
    images: tuple[SlaDashboardCommentImage, ...]
