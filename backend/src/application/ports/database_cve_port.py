# backend/src/application/ports/database_cve_port.py
from collections.abc import Callable
from typing import Protocol

from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseFeed, DatabaseFeedData, DatabaseTarget


class DatabaseCvePort(Protocol):
    targets: tuple[DatabaseTarget, ...]

    async def fetch(self, target: DatabaseTarget, feed: DatabaseFeed) -> DatabaseFeedData: ...

    def validate(self, target: DatabaseTarget, version: str) -> None: ...

    def matcher(self, target: DatabaseTarget, version: str, data: tuple[DatabaseFeedData, ...]) -> Callable[[DatabaseAdvisory], bool] | None: ...

    def coverage_note(self, target: DatabaseTarget, version: str, data: tuple[DatabaseFeedData, ...]) -> str | None: ...

    def compare_versions(self, target: DatabaseTarget, left: str, right: str) -> int: ...
