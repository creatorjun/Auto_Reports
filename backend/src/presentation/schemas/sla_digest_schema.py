# backend/src/presentation/schemas/sla_digest_schema.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class SlaDigestTriggerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: StrictBool = False


class SlaDigestTriggerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal["sent", "no_matches", "already_sent", "preview"]
    ticket_count: int = Field(ge=0)
    sla_count: int = Field(ge=0)
    recipient_count: int = Field(ge=0)
    generated_at: datetime
