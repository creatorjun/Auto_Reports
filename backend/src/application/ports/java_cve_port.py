# backend/src/application/ports/java_cve_port.py
from collections.abc import Callable
from typing import Protocol

from src.domain.entities.java_cve import JavaAdvisory, JavaFeed, JavaFeedData, JavaTarget


class JavaCvePort(Protocol):
    targets: tuple[JavaTarget, ...]

    async def fetch(self, target: JavaTarget, feed: JavaFeed) -> JavaFeedData: ...

    def validate(self, target: JavaTarget, version: str) -> None: ...

    def matcher(self, target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]) -> Callable[[JavaAdvisory], bool] | None: ...

    def coverage_note(self, target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]) -> str | None: ...

    def compare_versions(self, target: JavaTarget, left: str, right: str) -> int: ...
