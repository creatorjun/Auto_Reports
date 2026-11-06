# backend/src/application/ports/kernel_cve_port.py
from typing import Protocol

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeed, KernelFeedData, KernelTarget


class KernelCvePort(Protocol):
    targets: tuple[KernelTarget, ...]

    async def fetch(self, target: KernelTarget, feed: KernelFeed) -> KernelFeedData: ...

    def validate(self, target: KernelTarget, build: KernelBuild) -> None: ...

    def matches(self, target: KernelTarget, build: KernelBuild, advisory: KernelAdvisory) -> bool: ...

    def same_branch(self, build: KernelBuild, advisory: KernelAdvisory) -> bool: ...

    def coverage_note(self, target: KernelTarget, build: KernelBuild, data: tuple[KernelFeedData, ...]) -> str | None: ...

    def compare_versions(self, left: str, right: str) -> int: ...


KernelSnapshotPort = AdvisorySnapshotPort[KernelFeedData]
