# backend/src/application/ports/issue_management_snapshot_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.widget_data import RecentIssueDetail


@dataclass(frozen=True)
class IssueManagementSnapshot:
    issues: tuple[RecentIssueDetail, ...]
    synced_at: datetime
    full_synced_at: datetime


class IssueManagementSnapshotPort(ABC):
    @abstractmethod
    async def load(self, project_key: str) -> IssueManagementSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, project_key: str, snapshot: IssueManagementSnapshot) -> IssueManagementSnapshot:
        raise NotImplementedError
