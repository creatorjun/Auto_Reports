# backend/src/infrastructure/external/issue_query.py
import re

from src.application.ports.issue_query import IssueOrder, IssueQuery


def _quoted(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def compile_issue_query(query: IssueQuery) -> str:
    if isinstance(query, str):
        return query
    conditions: list[str] = []
    if query.project is not None:
        conditions.append(f"project = {_quoted(query.project)}")
    if query.reporters is not None:
        if not query.reporters:
            raise ValueError("Reporter selection must not be empty")
        conditions.append(f"reporter IN ({', '.join(map(_quoted, query.reporters))})")
    if query.reporter is not None:
        conditions.append(f"reporter = {_quoted(query.reporter)}")
    if query.keys is not None:
        if not query.keys or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*-\d+", key) for key in query.keys):
            raise ValueError("Invalid issue key selection")
        conditions.append(f"issuekey IN ({', '.join(query.keys)})")
    if query.updated_within_minutes is not None:
        minutes = query.updated_within_minutes
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
            raise ValueError("Update window must be nonnegative minutes")
        conditions.append(f'updated >= "-{minutes}m"')
    if not conditions:
        raise ValueError("Issue selection must not be empty")
    ordering = {
        IssueOrder.NONE: "",
        IssueOrder.NEWEST: " ORDER BY created DESC",
        IssueOrder.NEWEST_WITH_KEY: " ORDER BY created DESC, key DESC",
        IssueOrder.OLDEST_WITH_KEY: " ORDER BY created ASC, issuekey ASC",
    }
    return " AND ".join(conditions) + ordering[query.order]
