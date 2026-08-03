# backend/src/presentation/api/v1/partners.py
from fastapi import APIRouter, HTTPException, Request

from src.application.use_cases.partner_use_case import PartnerUseCase
from src.presentation.schemas.partner_schema import (
    PartnerOrgsResponse,
    PartnerIssuesResponse,
)

router = APIRouter(prefix="/partners", tags=["partners"])


def _get_use_case(request: Request) -> PartnerUseCase:
    return request.app.state.container.partner_use_case()


@router.get("/organizations", response_model=PartnerOrgsResponse)
async def get_organizations(request: Request):
    use_case = _get_use_case(request)
    orgs     = await use_case.get_organizations()
    return PartnerOrgsResponse(organizations=orgs)


@router.get("/issues", response_model=PartnerIssuesResponse)
async def get_partner_issues(
    request:    Request,
    org_name:   str | None = None,
    account_id: str | None = None,
):
    if not org_name and not account_id:
        raise HTTPException(
            status_code=422,
            detail="org_name 또는 account_id 중 하나는 필수입니다.",
        )

    use_case = _get_use_case(request)

    if org_name:
        issues = await use_case.get_issues_by_org(org_name)
    else:
        issues = await use_case.get_issues_by_member(account_id)  # type: ignore[arg-type]

    return PartnerIssuesResponse(issues=issues, total=len(issues))
