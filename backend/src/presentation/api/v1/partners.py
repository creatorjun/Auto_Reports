# backend/src/presentation/api/v1/partners.py
from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.partner_use_case import PartnerUseCase
from src.presentation.api.deps import get_partner_use_case
from src.presentation.schemas.partner_schema import (
    PartnerOrgsResponse,
    PartnerMembersResponse,
    PartnerIssuesResponse,
)

router = APIRouter(prefix="/partners", tags=["partners"])


@router.get("/organizations", response_model=PartnerOrgsResponse)
async def get_organizations(
    use_case: PartnerUseCase = Depends(get_partner_use_case),
):
    orgs = await use_case.get_organizations()
    return PartnerOrgsResponse(organizations=orgs)


@router.get("/organizations/{org_id}/members", response_model=PartnerMembersResponse)
async def get_members(
    org_id: str,
    use_case: PartnerUseCase = Depends(get_partner_use_case),
):
    members = await use_case.get_members(org_id)
    return PartnerMembersResponse(org_id=org_id, members=members)


@router.get("/issues", response_model=PartnerIssuesResponse)
async def get_partner_issues(
    org_id: str | None = None,
    account_id: str | None = None,
    use_case: PartnerUseCase = Depends(get_partner_use_case),
):
    if not org_id and not account_id:
        raise HTTPException(
            status_code=422,
            detail="org_id 또는 account_id 중 하나는 필수입니다.",
        )
    if org_id:
        issues = await use_case.get_issues_by_org(org_id)
    else:
        issues = await use_case.get_issues_by_member(account_id)
    return PartnerIssuesResponse(issues=issues, total=len(issues))
