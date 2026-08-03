# backend/src/presentation/api/v1/partners.py
from fastapi import APIRouter, HTTPException, Request

from src.application.use_cases.partner_use_case import PartnerUseCase
from src.presentation.schemas.partner_schema import (
    PartnerOrgsResponse,
    PartnerMembersResponse,
    PartnerIssuesResponse,
)

router = APIRouter(prefix="/partners", tags=["partners"])


def _uc(request: Request) -> PartnerUseCase:
    return request.app.state.container.partner_use_case()


@router.get("/organizations", response_model=PartnerOrgsResponse)
async def get_organizations(request: Request):
    orgs = await _uc(request).get_organizations()
    return PartnerOrgsResponse(organizations=orgs)


@router.get("/organizations/{org_id}/members", response_model=PartnerMembersResponse)
async def get_members(org_id: str, request: Request):
    members = await _uc(request).get_members(org_id)
    return PartnerMembersResponse(org_id=org_id, members=members)


@router.get("/issues", response_model=PartnerIssuesResponse)
async def get_partner_issues(
    request:    Request,
    org_id:     str | None = None,
    account_id: str | None = None,
):
    if not org_id and not account_id:
        raise HTTPException(
            status_code=422,
            detail="org_id 또는 account_id 중 하나는 필수입니다.",
        )
    uc = _uc(request)
    if org_id:
        issues = await uc.get_issues_by_org(org_id)
    else:
        issues = await uc.get_issues_by_member(account_id)  # type: ignore[arg-type]
    return PartnerIssuesResponse(issues=issues, total=len(issues))
