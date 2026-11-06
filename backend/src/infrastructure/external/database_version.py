# backend/src/infrastructure/external/database_version.py
import re
from datetime import date, datetime, timezone
from functools import lru_cache

from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseFeedData


@lru_cache(maxsize=4096)
def version_parts(value: str):
    match = re.fullmatch(r"([1-9][0-9]?(?:\.(?:0|[1-9][0-9]{0,3})){1,3})([a-z]?)", value)
    if not match:
        raise ValueError("정식 데이터베이스 서버 버전을 입력하세요. 예: 10.11.6, 8.0.36, 16.4")
    return tuple(int(x) for x in match[1].split(".")), match[2]


def validate_version(target_id: str, version: str) -> None:
    numbers, suffix = version_parts(version)
    size = len(numbers)
    if target_id == "postgresql":
        valid = size == (2 if numbers[0] >= 10 else 3) and not suffix
    elif target_id == "mariadb":
        valid = size == 3
    else:
        valid = 3 <= size <= 4 and not suffix
    if not valid:
        raise ValueError("선택한 제품의 정식 서버 버전을 패치 번호까지 입력하세요.")


def series_for(target_id: str, version: str) -> str:
    nums, _ = version_parts(version)
    return str(nums[0]) if target_id == "postgresql" and nums[0] >= 10 else f"{nums[0]}.{nums[1]}"


def compare_versions(left: str, right: str) -> int:
    ln, ls = version_parts(left)
    rn, rs = version_parts(right)
    a, b = (ln + (0,) * (4 - len(ln)), ls), (rn + (0,) * (4 - len(rn)), rs)
    return (a > b) - (a < b)


def score_severity(score: float | None):
    if score is None or score == 0:
        return "unknown"
    if score >= 9:
        return "critical"
    if score >= 7:
        return "high"
    return "medium" if score >= 4 else "low"


def matcher(target_id: str, version: str, data: tuple[DatabaseFeedData, ...]):
    series = series_for(target_id, version)
    rows = [row for feed in data for row in feed.advisories if row.series == series]
    if not any(row.fixed_version or row.affected_through or row.affected_version for row in rows):
        return None
    patched = {r.cve_id for r in rows if r.fixed_version and compare_versions(version, r.fixed_version) >= 0}

    def matches(row: DatabaseAdvisory):
        if row.series != series or row.cve_id in patched:
            return False
        if row.affected_version:
            return compare_versions(version, row.affected_version) == 0
        if row.affected_from:
            lower = compare_versions(version, row.affected_from)
            if lower < 0 or (lower == 0 and not row.affected_from_inclusive):
                return False
        if row.affected_through:
            upper = compare_versions(version, row.affected_through)
            return upper < 0 or (upper == 0 and row.affected_through_inclusive)
        return row.fixed_version is not None and compare_versions(version, row.fixed_version) < 0

    return matches


def coverage_note(target_id: str, version: str, data: tuple[DatabaseFeedData, ...]) -> str | None:
    series = series_for(target_id, version)
    rows = [r for part in data for r in part.advisories if r.series == series]
    builds = [b for part in data for b in part.builds if b.series == series]
    notes = []
    if False in {b.supported for b in builds} and not any(b.supported for b in builds):
        notes.append("공급자가 지원 종료로 표시한 계열입니다.")
    if not rows:
        notes.append("이 계열을 명시한 버전별 취약점 권고를 확인할 수 없습니다.")
    elif any(not (r.fixed_version or r.affected_version or r.affected_through) for r in rows):
        notes.append("일부 권고가 패치 번호를 명시하지 않아 해당 CVE의 적용 여부를 확인할 수 없습니다.")
    if any(r.series == series.split(".")[0] + ".*" for part in data for r in part.advisories):
        notes.append("일부 과거 권고의 버전 표기가 모호해 해당 CVE는 비교에서 제외했습니다.")
    if rows and target_id == "mysql":
        dated = [r.issued_at for r in rows if r.issued_at]
        if not dated:
            notes.append("이 계열의 근거는 2022년 1월까지의 이전 Oracle 권고에 한정됩니다.")
        elif (datetime.now(timezone.utc).date() - date.fromisoformat(max(dated))).days > 365:
            notes.append(f"이 계열이 명시된 마지막 Oracle 권고는 {max(dated)}입니다. 이후 공개된 취약점의 적용 여부는 확인되지 않았습니다.")
    if not any(compare_versions(version, b.version) == 0 for b in builds):
        notes.append("입력한 버전은 수집한 릴리스·권고 목록에서 확인되지 않았습니다.")
    return " ".join(notes) or None
