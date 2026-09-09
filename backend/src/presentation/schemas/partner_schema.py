# backend/src/presentation/schemas/partner_schema.py
from pydantic import BaseModel, ConfigDict


class PartnerOrgSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    issue_count: int


class PartnerOrgsResponse(BaseModel):
    organizations: list[PartnerOrgSchema]


class PartnerMemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    display_name: str
    email: str


class PartnerMembersResponse(BaseModel):
    org_id: str
    members: list[PartnerMemberSchema]


class RecentIssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
