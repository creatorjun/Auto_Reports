# backend/src/presentation/api/v1/cve_inventory.py
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.application.use_cases.cve_inventory import CveInventoryUseCase, CveRefreshThrottled
from src.presentation.api.deps import ApiServices, get_api_services
from src.presentation.schemas.cve_inventory import CveInventoryPackagesResponse, CveInventoryResponse


router = APIRouter(prefix="/cve-inventory", tags=["cve-inventory"])


def get_inventory_service(services: ApiServices = Depends(get_api_services)) -> CveInventoryUseCase:
    service = getattr(services, "cve_inventory", None)
    if service is None:
        raise HTTPException(status_code=503, detail="CVE 인벤토리 서비스가 준비되지 않았습니다.", headers={"Cache-Control": "no-store"})
    return service


@router.get("", response_model=CveInventoryResponse)
async def get_cve_inventory(
    response: Response,
    severity: Literal["all", "critical", "high", "medium", "low", "unknown"] = "all",
    search: str = Query(default="", max_length=300),
    ecosystem: str = Query(default="all", max_length=100),
    impact: Literal["all", "affected", "not_affected", "unknown"] = "all",
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    sort: Literal["severity", "published", "modified", "package", "newest"] = "severity",
    service: CveInventoryUseCase = Depends(get_inventory_service),
) -> CveInventoryResponse:
    response.headers["Cache-Control"] = "no-store"
    return CveInventoryResponse.model_validate(await service.get_snapshot(
        severity=severity, search=search, ecosystem=ecosystem, impact=impact, page=page, page_size=page_size, sort=sort,
    ))


@router.post("/refresh", response_model=CveInventoryResponse)
async def refresh_cve_inventory(
    response: Response, service: CveInventoryUseCase = Depends(get_inventory_service),
) -> CveInventoryResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return CveInventoryResponse.model_validate(await service.get_snapshot(refresh=True))
    except CveRefreshThrottled as error:
        raise HTTPException(status_code=429, detail=str(error), headers={
            "Retry-After": str(error.retry_after_seconds), "Cache-Control": "no-store",
        }) from error


@router.get("/packages", response_model=CveInventoryPackagesResponse)
async def get_cve_inventory_packages(
    response: Response,
    search: str = Query(default="", max_length=300),
    status: Literal["all", "pending", "ok", "stale", "error", "unmapped"] = "all",
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    service: CveInventoryUseCase = Depends(get_inventory_service),
) -> CveInventoryPackagesResponse:
    response.headers["Cache-Control"] = "no-store"
    return CveInventoryPackagesResponse.model_validate(await service.get_packages(search=search, status=status, page=page, page_size=page_size))
