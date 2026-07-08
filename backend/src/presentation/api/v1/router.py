# backend/src/presentation/api/v1/router.py
from fastapi import APIRouter
from src.presentation.api.v1 import reports, trigger, config, search

router = APIRouter(prefix="/api/v1")
router.include_router(reports.router)
router.include_router(trigger.router)
router.include_router(config.router)
router.include_router(search.router)
