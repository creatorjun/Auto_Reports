# backend/src/presentation/schemas/partner_schema.py
from pydantic import BaseModel


class PartnerMemberSchema(BaseModel):
    account_id: str
    display_name: str


class PartnerOrgSchema(BaseModel):
    id: str
    name: str
    members: list[PartnerMemberSchema]


class PartnerOrgsResponse(BaseModel):
    organizations: list[PartnerOrgSchema]


class RecentIssueSchema(BaseModel):
    key: str
    summary: str
    type: str
    status: str
    stage_index: int
    created: str
    elapsed_days: int
    reporter: str
    tac_team: str


class PartnerIssuesResponse(BaseModel):
    issues: list[RecentIssueSchema]
    total: int
