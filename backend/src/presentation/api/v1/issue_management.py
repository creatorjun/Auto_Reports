# backend/src/presentation/api/v1/issue_management.py
from fastapi import APIRouter, Depends, HTTPException, Response

from src.presentation.api.deps import ApiServices, get_api_services

router = APIRouter(prefix="/issue-management", tags=["issue-management"])


@router.get("/issues")
async def list_issues(response: Response, services: ApiServices = Depends(get_api_services)):
    response.headers["Cache-Control"] = "no-store"
    if services.issue_management is None:
        raise HTTPException(status_code=503, detail="Issue management is unavailable")
    return await services.issue_management.list_issues()
