# backend/src/application/ports/issue_notification_renderer_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.widget_data import RecentIssueDetail


class IssueNotificationRendererPort(ABC):
    @abstractmethod
    def render_todo(
        self, issues: list[RecentIssueDetail], jira_base_url: str, now: datetime,
    ) -> str: ...

    @abstractmethod
    def render_tac_assigned(
        self, issue: RecentIssueDetail, jira_base_url: str, now: datetime,
    ) -> str: ...
