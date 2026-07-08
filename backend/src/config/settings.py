# backend/src/config/settings.py
"""Backward-compatibility shim.

실제 Settings 정의는 infrastructure/config/settings.py 로 이동되었습니다.
이 파일은 기존 import 경로가 동작하도록 유지합니다.
"""
from src.infrastructure.config.settings import Settings, get_settings  # noqa: F401
