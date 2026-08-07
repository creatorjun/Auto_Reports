# backend/src/infrastructure/config/settings.py
import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_KST = ZoneInfo("Asia/Seoul")


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

    report_retention_weeks: int = Field(
        default=52,
        description="보고서 DB 보존 기간(주). 0이면 자동 삭제 비활성화.",
    )

    login: bool = Field(default=False, alias="LOGIN", validation_alias="LOGIN")
    admin_username: str = Field(default="admin", alias="ADMIN", validation_alias="ADMIN")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD", validation_alias="ADMIN_PASSWORD")
    superadmin_username: str = Field(default="", alias="SUPERADMIN", validation_alias="SUPERADMIN")
    superadmin_password: str = Field(default="", alias="SUPERADMIN_PASSWORD", validation_alias="SUPERADMIN_PASSWORD")
    jwt_secret: str = Field(default="please-set-JWT_SECRET-in-env", alias="JWT_SECRET", validation_alias="JWT_SECRET")
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE", validation_alias="COOKIE_SECURE")
    storage_dir: str = "/app/storage"
    credential_encryption_key: str = Field(default="", alias="CREDENTIAL_ENCRYPTION_KEY", validation_alias="CREDENTIAL_ENCRYPTION_KEY")

    smtp_host: str = Field(default="", alias="SMTP_HOST", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT", validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD", validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM", validation_alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS", validation_alias="SMTP_USE_TLS")
    smtp_start_tls: bool = Field(default=True, alias="SMTP_START_TLS", validation_alias="SMTP_START_TLS")
    notify_todo_enabled: bool = Field(default=False, alias="NOTIFY_TODO_ENABLED", validation_alias="NOTIFY_TODO_ENABLED")
    notify_todo_cron: str = Field(default="0 9 * * 1-5", alias="NOTIFY_TODO_CRON", validation_alias="NOTIFY_TODO_CRON")
    notify_todo_to: list[str] = Field(default=[], alias="NOTIFY_TODO_TO", validation_alias="NOTIFY_TODO_TO")

    @property
    def year_start(self) -> int:
        return datetime.datetime.now(_KST).year

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
