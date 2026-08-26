# backend/src/presentation/schemas/sla_dashboard_schema.py
from pydantic import BaseModel, ConfigDict


class SlaDashboardIssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    type: str
    summary: str
    created: str
    updated: str
    status: str


class SlaDashboardCommentImageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attachment_id: str
    alt: str


class SlaDashboardCommentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author: str
    body: str
    created: str
    updated: str
    images: tuple[SlaDashboardCommentImageSchema, ...]
