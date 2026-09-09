# backend/src/domain/entities/partner.py
from dataclasses import dataclass


@dataclass(frozen=True)
class PartnerOrganization:
    id: str
    name: str
    issue_count: int = 0


@dataclass(frozen=True)
class PartnerMember:
    account_id: str
    display_name: str
    email: str


@dataclass(frozen=True)
class PartnerIssue:
    key: str
    summary: str
    type: str
    status: str
    stage_index: int
    created: str
    elapsed_days: int
    reporter: str
    tac_team: str
