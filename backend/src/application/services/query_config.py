# backend/src/application/services/query_config.py
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryConfig:
    """Application 레이어가 주입받는 순수 쿼리 설정 DTO.

    Infrastructure(Settings)와 직접 결합하지 않도록 Container가 조립한다.
    """
    project_key: str
    issue_types: list[str]
    active_statuses: list[str]
    closed_statuses: list[str]
    sla_threshold_days: int
    year_start: int
