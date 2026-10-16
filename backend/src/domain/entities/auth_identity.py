# backend/src/domain/entities/auth_identity.py
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AuthIdentity:
    username: str
    display_name: str
    auth_provider: Literal["local", "jira"] = "local"
    session_expires_at: int | None = None
    profile_version: int | None = None
