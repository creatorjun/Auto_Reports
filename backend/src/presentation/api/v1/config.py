# backend/src/presentation/api/v1/config.py
from fastapi import APIRouter, Request

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(request: Request):
    container = request.app.state.container
    return {"jira_base_url": container.jira_base_url}
