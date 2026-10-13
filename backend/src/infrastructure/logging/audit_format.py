# backend/src/infrastructure/logging/audit_format.py
import json
import re
from collections.abc import Mapping

_SECRET_KEY = re.compile(r"password|passwd|secret|token|authorization|cookie|credential|api.?key|private.?key", re.IGNORECASE)
_INLINE_SECRET = re.compile(r"(?i)(password|passwd|secret|token|authorization|cookie|credential|api[_-]?key|private[_-]?key)(\s*[=:]\s*)([^\s&|,;]+)")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def safe_text(value: object, limit: int = 4000) -> str:
    text = str(value).replace("\r", "\\r").replace("\n", "\\n").replace("\x00", "")
    text = _INLINE_SECRET.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    text = _BEARER.sub("Bearer [REDACTED]", text)
    return text if len(text) <= limit else f"{text[:limit - 12]} [TRUNCATED]"


def safe_fields(fields: Mapping[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in list(fields.items())[:32]:
        key = safe_text(key, 80)
        if _SECRET_KEY.search(key):
            result[key] = "[REDACTED]"
        elif isinstance(value, (Mapping, list, tuple)):
            result[key] = safe_text(json.dumps(_safe_value(value), ensure_ascii=False), 1000)
        elif value is not None:
            result[key] = safe_text(value, 1000)
    return result


def _safe_value(value: object, depth: int = 0) -> object:
    if depth >= 4:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        return {safe_text(key, 80): "[REDACTED]" if _SECRET_KEY.search(str(key)) else _safe_value(item, depth + 1) for key, item in list(value.items())[:64]}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth + 1) for item in value[:64]]
    return safe_text(value)
