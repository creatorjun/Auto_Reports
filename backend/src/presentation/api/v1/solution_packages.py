# backend/src/presentation/api/v1/solution_packages.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from src.domain.entities.solution_package import SolutionPackage
from src.presentation.api.deps import ApiServices, get_api_services

router = APIRouter(prefix="/solution-packages", tags=["solution-packages"])


class SolutionPackagesResponse(BaseModel):
    packages: tuple[SolutionPackage, ...]


@router.get("")
def get_solution_packages(
    response: Response,
    product: str = Query(min_length=1, max_length=32),
    version: str | None = Query(default=None, min_length=1, max_length=32),
    services: ApiServices = Depends(get_api_services),
) -> SolutionPackagesResponse:
    packages = services.read_solution_packages(product, version)
    if packages is None:
        raise HTTPException(422, "지원하지 않는 제품·버전 조합입니다.")
    response.headers["Cache-Control"] = "no-store"
    return SolutionPackagesResponse(packages=packages)
