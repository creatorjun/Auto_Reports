# backend/src/domain/services/issue_type_policy.py
_LICENSE_ISSUE_TYPES = frozenset({
    "라이선스",
    "라이센스",
    "라이선스 요청",
    "라이센스 요청",
})


def is_license_issue_type(issue_type: str) -> bool:
    return issue_type.strip() in _LICENSE_ISSUE_TYPES
