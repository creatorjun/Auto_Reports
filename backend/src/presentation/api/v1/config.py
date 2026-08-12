# backend/src/presentation/api/v1/config.py
from fastapi import APIRouter, Depends

from src.presentation.api.deps import ApiServices, get_api_services

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(services: ApiServices = Depends(get_api_services)):
    return {"jira_base_url": services.jira_base_url}
