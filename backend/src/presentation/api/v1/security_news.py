# backend/src/presentation/api/v1/security_news.py
from fastapi import APIRouter, Depends, HTTPException, Response

from src.application.use_cases.security_news import SecurityNewsRefreshThrottled
from src.presentation.api.deps import ApiServices, get_api_services
from src.presentation.schemas.security_news import SecurityNewsResponse


router = APIRouter(prefix="/security-news", tags=["security-news"])


async def news_snapshot(response: Response, services: ApiServices, *, refresh: bool = False) -> SecurityNewsResponse:
    response.headers["Cache-Control"] = "no-store"
    if services.security_news is None:
        raise HTTPException(
            status_code=503, detail="보안 뉴스 서비스가 준비되지 않았습니다.",
            headers={"Cache-Control": "no-store"},
        )
    try:
        snapshot = await services.security_news.get_snapshot(refresh=refresh)
    except SecurityNewsRefreshThrottled as error:
        raise HTTPException(
            status_code=429, detail=str(error),
            headers={"Retry-After": str(error.retry_after_seconds), "Cache-Control": "no-store"},
        ) from error
    return SecurityNewsResponse.model_validate(snapshot)


@router.get("", response_model=SecurityNewsResponse)
async def get_security_news(
    response: Response,
    services: ApiServices = Depends(get_api_services),
) -> SecurityNewsResponse:
    return await news_snapshot(response, services)


@router.post("/refresh", response_model=SecurityNewsResponse)
async def refresh_security_news(
    response: Response,
    services: ApiServices = Depends(get_api_services),
) -> SecurityNewsResponse:
    return await news_snapshot(response, services, refresh=True)
