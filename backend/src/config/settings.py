# backend/src/config/settings.py
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
    cors_origins: list[str] = ["*"]
    issue_types: list[str] = ["인시던트", "개선", "CVE", "서비스 요청"]
    active_statuses: list[str] = [
        "할 일", "이슈 리뷰 중", "연구소 대기 중", "연구소 검토 중",
        "구현 중", "배포 파일 검토 중", "자료 요청 중", "결과 대기 중",
        "보류 중", "영업본부 검토중"
    ]
    closed_statuses: list[str] = ["Closed", "반려됨", "중복 이슈", "취소됨"]

    @property
    def year_start(self) -> int:
        """w8/w9 연도 누적 쿼리에 사용할 연도. 현재 연도를 자동 반환."""
        return datetime.date.today().year

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
