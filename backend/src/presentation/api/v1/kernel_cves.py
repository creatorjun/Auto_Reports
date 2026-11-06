# backend/src/presentation/api/v1/kernel_cves.py
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from src.application.use_cases.kernel_cves import KernelCveUseCase, KernelReleases, KernelResults, UpstreamResults
from src.domain.entities.kernel_cve import KernelBuild
from src.presentation.api.deps import ApiServices, get_api_services


router = APIRouter(prefix="/kernel-cves", tags=["kernel-cves"])
SeverityFilter = Literal["all", "critical", "high", "medium", "low", "unknown"]


class KernelTargetOption(BaseModel):
    id: str
    label: str
    packages: tuple[str, ...]
    architectures: tuple[str, ...]
    coverage: str
    available: bool


class KernelTargets(BaseModel):
    targets: tuple[KernelTargetOption, ...]


def get_service(response: Response, services: ApiServices = Depends(get_api_services)) -> KernelCveUseCase:
    response.headers["Cache-Control"] = "no-store"
    if services.kernel_cves is None:
        raise HTTPException(503, detail="커널 취약점 서비스를 준비하고 있습니다.", headers={"Cache-Control": "no-store"})
    return services.kernel_cves


@router.get("/targets")
async def get_targets(service: KernelCveUseCase = Depends(get_service)) -> KernelTargets:
    return KernelTargets(targets=tuple(KernelTargetOption.model_validate(t, from_attributes=True) for t in service.targets))


@router.get("/releases")
async def get_releases(
    target: str = Query(min_length=1, max_length=64),
    package: str = Query(min_length=1, max_length=64),
    architecture: str = Query(min_length=1, max_length=24),
    service: KernelCveUseCase = Depends(get_service),
) -> KernelReleases:
    try:
        return await service.releases(target, package, architecture)
    except ValueError as error:
        raise HTTPException(422, str(error), headers={"Cache-Control": "no-store"}) from error


@router.get("")
async def get_kernel_cves(
    target: str = Query(min_length=1, max_length=64),
    package: str = Query(min_length=1, max_length=64),
    architecture: str = Query(min_length=1, max_length=24),
    version: str = Query(min_length=1, max_length=128),
    severity: SeverityFilter = "all",
    search: str = Query(default="", max_length=160),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    service: KernelCveUseCase = Depends(get_service),
) -> KernelResults:
    try:
        return await service.find(target, KernelBuild(package, architecture, version), severity, search, page, page_size)
    except ValueError as error:
        raise HTTPException(422, str(error), headers={"Cache-Control": "no-store"}) from error


@router.get("/upstream")
async def get_upstream(
    target: str = Query(min_length=1, max_length=64),
    search: str = Query(default="", max_length=160),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: KernelCveUseCase = Depends(get_service),
) -> UpstreamResults:
    try:
        return await service.upstream(target, search, page, page_size)
    except ValueError as error:
        raise HTTPException(422, str(error), headers={"Cache-Control": "no-store"}) from error
