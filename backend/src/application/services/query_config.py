# backend/src/application/services/query_config.py
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryConfig:
    project_key: str
    issue_types: list[str]
    active_statuses: list[str]
    closed_statuses: list[str]
    sla_threshold_days: int
    year_start: int
    jira_tac_assignee_field_id: str
    jira_qa_assignee_field_id: str
