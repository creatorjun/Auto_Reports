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
    issue_types: list[str] = ["\uc778\uc2dc\ub358\ud2b8", "\uac1c\uc120", "CVE", "\uc11c\ube44\uc2a4 \uc694\uccad"]
    active_statuses: list[str] = [
        "\ud560 \uc77c", "\uc774\uc288 \ub9ac\ubdf0 \uc911", "\uc5f0\uad6c\uc18c \ub300\uae30 \uc911", "\uc5f0\uad6c\uc18c \uac80\ud1a0 \uc911",
        "\uad6c\ud604 \uc911", "\ubc30\ud3ec \ud30c\uc77c \uac80\ud1a0 \uc911", "\uc790\ub8cc \uc694\uccad \uc911", "\uacb0\uacfc \ub300\uae30 \uc911",
        "\ubcf4\ub958 \uc911", "\uc601\uc5c5\ubcf8\ubd80 \uac80\ud1a0\uc911"
    ]
    closed_statuses: list[str] = ["Closed", "\ubc18\ub824\ub428", "\uc911\ubcf5 \uc774\uc288", "\ucde8\uc18c\ub428"]

    login: bool = False
    admin_username: str = "admin"
    admin_password: str = ""
    jwt_secret: str = "please-set-JWT_SECRET-in-env"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    @property
    def year_start(self) -> int:
        return datetime.date.today().year

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True
        fields = {
            "login": {"env": "LOGIN"},
            "admin_username": {"env": "Admin"},
            "admin_password": {"env": "Admin_PASSWORD"},
            "jwt_secret": {"env": "JWT_SECRET"},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
