# backend/src/presentation/api/v1/vendor_cve_routes.py
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from src.application.services.vendor_cves import VendorCves
from src.presentation.api.deps import ApiServices, get_api_services


class VendorOption(BaseModel):
    id: str
    label: str
    coverage: str
    available: bool


class VendorTargets(BaseModel):
    targets: tuple[VendorOption, ...]


def vendor_cve_router(
    name: str, select: Callable[[ApiServices], VendorCves | None], releases_model, results_model,
) -> APIRouter:
    router = APIRouter(prefix=f"/{name}", tags=[name])

    def get_service(response: Response, services: ApiServices = Depends(get_api_services)) -> VendorCves:
        response.headers["Cache-Control"] = "no-store"
        service = select(services)
        if service is None:
            raise HTTPException(503, detail="취약점 서비스를 준비하고 있습니다.", headers={"Cache-Control": "no-store"})
        return service

    @router.get("/targets")
    async def get_targets(service: VendorCves = Depends(get_service)) -> VendorTargets:
        return VendorTargets(targets=tuple(VendorOption.model_validate(t, from_attributes=True) for t in service.targets))

    @router.get("/releases", response_model=releases_model)
    async def get_releases(target: str = Query(min_length=1, max_length=30), service: VendorCves = Depends(get_service)):
        try:
            return await service.releases(target)
        except ValueError as error:
            raise HTTPException(422, str(error), headers={"Cache-Control": "no-store"}) from error

    @router.get("", response_model=results_model)
    async def get_findings(
        target: str = Query(min_length=1, max_length=30), version: str = Query(min_length=1, max_length=128),
        severity: Literal["all", "critical", "high", "medium", "low", "unknown"] = "all",
        search: str = Query(default="", max_length=160), page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100), service: VendorCves = Depends(get_service),
    ):
        try:
            return await service.find(target, version, severity, search, page, page_size)
        except ValueError as error:
            raise HTTPException(422, str(error), headers={"Cache-Control": "no-store"}) from error

    return router
