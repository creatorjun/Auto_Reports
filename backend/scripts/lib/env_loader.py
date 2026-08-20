# backend/scripts/lib/env_loader.py
import os
from pathlib import Path

from dotenv import load_dotenv

_here = Path(__file__).parent.parent.parent
for _candidate in [_here / ".env", _here.parent / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break


def get_env(key: str) -> str:
    value = os.environ.get(key) or os.environ.get(key.upper())
    if not value:
        raise KeyError(f"환경변수 '{key}' 또는 '{key.upper()}'가 설정되지 않았습니다.")
    return value
