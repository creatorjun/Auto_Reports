# backend/src/presentation/api/v1/config.py
from fastapi import APIRouter
from src.config.settings import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config():
    s = get_settings()
    return {"jira_base_url": s.jira_base_url}
