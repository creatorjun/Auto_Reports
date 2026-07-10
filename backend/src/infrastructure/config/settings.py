# backend/src/infrastructure/config/settings.py
import datetime
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    gemini_api_key: str = ""
    ai_enabled: bool = True
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "db"
    db_name: str = "auto_reports"
    confluence_space_key: str = ""
    confluence_parent_page_id: str = ""
    schedule_cron: str = "0 23 * * 5"
    tz: str = "Asia/Seoul"
    project_key: str = "TACEA"
    sla_threshold_days: int = 30
    sla_initial_response_field_id: str = "customfield_12152"
    sla_resolution_field_id: str = "customfield_12151"
    jira_tac_assignee_field_id: str = "customfield_10859"
    jira_qa_assignee_field_id: str = "customfield_12222"
    cors_origins: list[str] = ["*"]
    issue_types: list[str] = ["인시던트", "개선", "CVE", "서비스 요청"]
    active_statuses: list[str] = [
        "할 일", "이슈 리뷰 중", "연구소 대기 중", "연구소 검토 중",
        "구현 중", "배포 파일 검토 중", "자료 요청 중", "결과 대기 중",
        "보류 중", "영업본부 검토중"
    ]
    closed_statuses: list[str] = ["Closed", "반려됨", "중복 이슈", "취소됨"]

    login: bool = False
    admin_username: str = "admin"
    admin_password: str = ""
    jwt_secret: str = "please-set-JWT_SECRET-in-env"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    storage_dir: str = "/app/storage"

    @property
    def year_start(self) -> int:
        return datetime.date.today().year

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "env_prefix": "",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
