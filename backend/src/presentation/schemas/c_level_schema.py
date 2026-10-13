# backend/src/presentation/schemas/c_level_schema.py
from pydantic import BaseModel, ConfigDict, Field


class CLevelCommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_token: str = Field(min_length=20, max_length=100)
    delay_reason: str = Field(default="", max_length=10000)
    action_taken: str = Field(default="", max_length=10000)
    prevention_plan: str = Field(default="", max_length=10000)
    included: bool = True


class CLevelSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_token: str = Field(min_length=20, max_length=100)
    title: str | None = Field(default=None, max_length=200)
