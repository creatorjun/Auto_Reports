# backend/src/presentation/api/v1/solution_packages.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from src.application.use_cases.solution_advisories import SolutionInventoryResult
from src.presentation.api.deps import ApiServices, get_api_services

router = APIRouter(prefix="/solution-packages", tags=["solution-packages"])


@router.get("")
async def get_solution_packages(
    response: Response,
    product: str = Query(min_length=1, max_length=32),
    version: str | None = Query(default=None, min_length=1, max_length=32),
    services: ApiServices = Depends(get_api_services),
) -> SolutionInventoryResult:
    inventory = await services.solution_cves.get(product, version)
    if inventory is None:
        raise HTTPException(422, "지원하지 않는 제품·버전 조합입니다.")
    response.headers["Cache-Control"] = "no-store"
    return inventory
