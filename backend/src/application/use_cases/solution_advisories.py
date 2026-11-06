# backend/src/application/use_cases/solution_advisories.py
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import lru_cache
import hashlib
import json

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.application.services.daily_advisories import AdvisoryCoverage, DailyAdvisories
from src.domain.entities.solution_package import SolutionFeedData, SolutionPackage


@dataclass(frozen=True)
class SolutionInventoryResult:
    packages: tuple[SolutionPackage, ...]
    coverage: AdvisoryCoverage | None


@dataclass(frozen=True)
class SolutionFeed:
    id: str
    label: str
    url: str


_FEEDS = tuple(
    SolutionFeed(ecosystem, f"OSV · {ecosystem}", f"https://storage.googleapis.com/osv-vulnerabilities/{ecosystem}/all.zip")
    for ecosystem in ("Maven", "npm")
)
_REGISTERED_RELEASE = ("eyeCloudXoar", "4.0_R2")


@dataclass(frozen=True)
class SolutionTarget:
    id: str
    packages: tuple[SolutionPackage, ...]
    feeds: tuple[SolutionFeed, ...] = _FEEDS
    available: bool = True


@lru_cache(maxsize=2)
def _target(product: str, version: str, packages: tuple[SolutionPackage, ...]) -> SolutionTarget:
    inventory = sorted((vars(package) for package in packages), key=lambda row: row["id"])
    identity = json.dumps([product, version, inventory], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return SolutionTarget(hashlib.sha256(identity.encode()).hexdigest(), packages)


class SolutionAdvisories(DailyAdvisories[SolutionTarget, SolutionFeed, SolutionFeedData]):
    def __init__(
        self, read_inventory: Callable[[str, str | None], tuple[SolutionPackage, ...] | None],
        match_packages: Callable[[tuple[SolutionPackage, ...], str], Awaitable[dict[str, tuple[str, ...] | None]]],
        store: AdvisorySnapshotPort[SolutionFeedData], clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__((), self._collect_matches, store, clock)
        self._read_inventory = read_inventory
        self._match_packages = match_packages

    async def _collect_matches(self, target: SolutionTarget, feed: SolutionFeed) -> SolutionFeedData:
        return SolutionFeedData(feed.id, await self._match_packages(target.packages, feed.id))

    async def refresh_scheduled(self) -> None:
        packages = await asyncio.to_thread(self._read_inventory, *_REGISTERED_RELEASE)
        if packages:
            await self._refresh_targets((_target(*_REGISTERED_RELEASE, packages),))

    async def get(self, product: str, version: str | None) -> SolutionInventoryResult | None:
        packages = await asyncio.to_thread(self._read_inventory, product, version)
        if packages is None:
            return None
        if not packages or (product, version) != _REGISTERED_RELEASE:
            return SolutionInventoryResult(packages, None)
        target = _target(*_REGISTERED_RELEASE, packages)
        coverage, parts = await self.read_coverage(target, target.feeds)
        confirmed = {
            key: ids for part in parts
            for key, ids in part.matches.items() if ids is not None
        }
        result = tuple(
            replace(row, cve_ids=confirmed[row.id], cve_basis="advisory") if row.id in confirmed else row
            for row in packages
        )
        reviewed = sum(row.cve_basis == "advisory" for row in result)
        note = (f"OSV 권고 대조 {reviewed}개 · 배포본 조사 결과 {len(result) - reviewed}개. "
                "출처별 마지막 성공 자료를 사용하며, 대조 결과가 없는 항목은 배포본 조사 결과를 표시합니다.")
        return SolutionInventoryResult(result, replace(coverage, coverage_note=note))
