# backend/src/presentation/api/v1/router.py
from fastapi import APIRouter, Depends
from src.presentation.api.v1 import auth, reports, trigger, config, search, storage
from src.presentation.api.v1.deps import require_auth

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(storage.preview_router)

_protected = APIRouter(dependencies=[Depends(require_auth)])
_protected.include_router(reports.router)
_protected.include_router(trigger.router)
_protected.include_router(config.router)
_protected.include_router(search.router)
_protected.include_router(storage.router)

router.include_router(_protected)
