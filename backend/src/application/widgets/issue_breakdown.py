# backend/src/application/widgets/issue_breakdown.py
from collections.abc import Iterable


def issue_type_name(issue: dict) -> str:
    fields = issue.get("fields") or {}
    return (fields.get("issuetype") or {}).get("name", "기타")


def issue_status_name(issue: dict) -> str:
    fields = issue.get("fields") or {}
    return (fields.get("status") or {}).get("name", "기타")


def count_issue_type_statuses(
    issues: Iterable[dict],
    controlled_types: Iterable[str],
) -> tuple[dict[str, int], int, dict[str, dict[str, int]]]:
    by_type = {issue_type: 0 for issue_type in controlled_types}
    always_included = 0
    by_status_type: dict[str, dict[str, int]] = {}

    for issue in issues:
        issue_type = issue_type_name(issue)
        status = issue_status_name(issue)
        if issue_type in by_type:
            by_type[issue_type] += 1
        else:
            always_included += 1
        status_types = by_status_type.setdefault(status, {})
        status_types[issue_type] = status_types.get(issue_type, 0) + 1

    return by_type, always_included, by_status_type
