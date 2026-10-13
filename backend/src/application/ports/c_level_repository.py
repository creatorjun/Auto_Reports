# backend/src/application/ports/c_level_repository.py
from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.c_level_history import CLevelComment, CLevelSnapshotSummary


class CLevelRepository(ABC):
    @abstractmethod
    async def get_comments(self, issue_keys: list[str]) -> list[CLevelComment]:
        raise NotImplementedError

    @abstractmethod
    async def save_comment(self, comment: CLevelComment) -> CLevelComment:
        raise NotImplementedError

    @abstractmethod
    async def save_snapshot(self, payload: dict[str, Any], title: str, actor: str) -> CLevelSnapshotSummary:
        raise NotImplementedError

    @abstractmethod
    async def list_snapshots(self, limit: int, offset: int) -> list[CLevelSnapshotSummary]:
        raise NotImplementedError

    @abstractmethod
    async def get_snapshot(self, snapshot_id: int) -> tuple[CLevelSnapshotSummary, dict[str, Any]] | None:
        raise NotImplementedError


class CLevelPreviewPort(ABC):
    @abstractmethod
    def put(self, payload: dict[str, Any], actor: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get(self, token: str, actor: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def replace(self, token: str, payload: dict[str, Any], actor: str) -> bool:
        raise NotImplementedError
