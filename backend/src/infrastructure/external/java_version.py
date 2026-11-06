# backend/src/infrastructure/external/java_version.py
import re
from functools import lru_cache


_LEGACY = re.compile(r"(?:1\.([78])\.0_|([78])u)([0-9]{1,4})(?:-?b([0-9]{1,3}))?")
_MODERN = re.compile(r"([1-9][0-9]?(?:\.(?:0|[1-9][0-9]{0,3})){0,6})(?:\+([0-9]{1,3})(?:-LTS)?)?")


@lru_cache(maxsize=4096)
def java_version(value: str) -> tuple[tuple[int, ...], int | None]:
    legacy = _LEGACY.fullmatch(value)
    if legacy:
        parts = [int(legacy[1] or legacy[2]), 0, int(legacy[3])]
        build = legacy[4]
    else:
        modern = _MODERN.fullmatch(value)
        if not modern or int(modern[1].partition(".")[0]) < 7:
            raise ValueError("Java 정식 릴리스 버전을 입력하세요. 예: 1.8.0_402, 8u402, 17.0.11+9")
        parts = [int(n) for n in modern[1].split(".")]
        build = modern[2]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts), int(build) if build is not None else None


def compare_java_versions(left: str, right: str) -> int:
    lv, lb = java_version(left)
    rv, rb = java_version(right)
    left_key, right_key = (lv, lb or 0), (rv, rb or 0)
    return (left_key > right_key) - (left_key < right_key)
