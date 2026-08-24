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
    issue_types: list[str] = ["\uc778\uc2dc\ub358\ud2b8", "\uac1c\uc120", "CVE", "\uc11c\ube44\uc2a4 \uc694\uccad", "\ub77c\uc774\uc120\uc2a4", "H/W \uc7a5\uc560 \uc694\uccad", "\uc2b9\uc778\ub41c \uc11c\ube44\uc2a4 \uc694\uccad"]
    active_statuses: list[str] = [
        "\ud560 \uc77c", "\uc774\uc288 \ub9ac\ubdf0 \uc911", "\uc5f0\uad6c\uc18c \ub300\uae30 \uc911", "\uc5f0\uad6c\uc18c \uac80\ud1a0 \uc911",
        "\uad6c\ud604 \uc911", "\ubc30\ud3ec \ud30c\uc77c \uac80\ud1a0 \uc911", "\uc790\ub8cc \uc694\uccad \uc911", "\uacb0\uacfc \ub300\uae30 \uc911",
        "\ubcf4\ub958 \uc911", "\uc601\uc5c5\ubcf8\ubd80 \uac80\ud1a0\uc911"
    ]
    closed_statuses: list[str] = ["Closed", "\ubc18\ub824\ub428", "\uc911\ubcf5 \uc774\uc288", "\ucde8\uc18c\ub428"]

    report_retention_weeks: int = Field(
        default=52,
        description="\ubcf4\uace0\uc11c DB \ubcf4\uc874 \uae30\uac04(\uc8fc). 0\uc774\uba74 \uc790\ub3d9 \uc0ad\uc81c \ube44\ud65c\uc131\ud654.",
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
    smtp_start_tls: bool = Field(default=False, alias="SMTP_START_TLS", validation_alias="SMTP_START_TLS")
    notify_todo_enabled: bool = Field(default=False, alias="NOTIFY_TODO_ENABLED", validation_alias="NOTIFY_TODO_ENABLED")
    notify_todo_to: list[str] = Field(default=[], alias="NOTIFY_TODO_TO", validation_alias="NOTIFY_TODO_TO")
    notify_tac_enabled: bool = Field(default=False, alias="NOTIFY_TAC_ENABLED", validation_alias="NOTIFY_TAC_ENABLED")
    notify_tac_to: list[str] = Field(default=[], alias="NOTIFY_TAC", validation_alias="NOTIFY_TAC")
    notify_tac_keyword: str = Field(default="\uc624\uacbd\uc11d", alias="NOTIFY_TAC_KEYWORD", validation_alias="NOTIFY_TAC_KEYWORD")

    refresh_report_enabled: bool = Field(default=True, alias="REFRESH_REPORT_ENABLED", validation_alias="REFRESH_REPORT_ENABLED")
    refresh_report_interval_minutes: int = Field(default=5, alias="REFRESH_REPORT_INTERVAL_MINUTES", validation_alias="REFRESH_REPORT_INTERVAL_MINUTES")

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
