# backend/src/application/use_cases/kernel_cves.py
import asyncio
from collections import OrderedDict, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cmp_to_key

from src.application.ports.kernel_cve_port import KernelCvePort, KernelSnapshotPort
from src.application.services.daily_advisories import AdvisoryCoverage, DailyAdvisories
from src.domain.entities.kernel_cve import (
    SEVERITIES, KernelAdvisory, KernelBuild, KernelFeed, KernelFeedData, KernelSeverity,
    KernelStatus, KernelTarget,
)


UPSTREAM_ID = "linux-upstream"


@dataclass(frozen=True)
class KernelReleases(AdvisoryCoverage):
    versions: tuple[str, ...]


@dataclass(frozen=True)
class KernelFix:
    advisory_id: str
    advisory_url: str
    issued_at: str | None
    fixed_version: str
    package: str
    architecture: str
    title: str | None


@dataclass(frozen=True)
class KernelFinding:
    cve_id: str
    severity: KernelSeverity
    summary: str | None
    fixes: tuple[KernelFix, ...]


@dataclass(frozen=True)
class KernelResults(AdvisoryCoverage):
    total: int | None
    page: int
    page_size: int
    severity_counts: dict[str, int]
    items: tuple[KernelFinding, ...]


@dataclass(frozen=True)
class UpstreamCve:
    cve_id: str
    title: str
    published_at: str | None
    url: str


@dataclass(frozen=True)
class UpstreamResults:
    status: KernelStatus
    refreshing: bool
    as_of: datetime | None
    total: int | None
    page: int
    page_size: int
    items: tuple[UpstreamCve, ...]


class KernelCveUseCase(DailyAdvisories[KernelTarget, KernelFeed, KernelFeedData]):
    def __init__(self, source: KernelCvePort, store: KernelSnapshotPort, clock: Callable[[], datetime] | None = None) -> None:
        self._source = source
        super().__init__(source.targets, source.fetch, store, clock)
        self.targets = tuple(target for target in source.targets if target.id != UPSTREAM_ID)
        self._upstream = next((target for target in source.targets if target.id == UPSTREAM_ID), None)
        self._index_lock = asyncio.Lock()
        self._indexes: OrderedDict[tuple, tuple[KernelFinding, ...]] = OrderedDict()
        self._upstream_indexes: dict[str, tuple[tuple, tuple[UpstreamCve, ...]]] = {}
        self._upstream_lock = asyncio.Lock()

    def _select(self, target_id: str, package: str, architecture: str) -> KernelTarget:
        target = next((item for item in self.targets if item.id == target_id), None)
        if target is None or not target.available:
            raise ValueError("조회할 수 없는 배포판입니다.")
        if package not in target.packages or architecture not in target.architectures:
            raise ValueError("배포판에서 지원하는 커널 패키지와 아키텍처를 선택하세요.")
        return target

    async def _coverage(self, target: KernelTarget, architecture: str | None = None):
        feeds = (feed for feed in target.feeds if not architecture or not feed.architectures or architecture in feed.architectures)
        return await self.read_coverage(target, feeds)

    async def releases(self, target_id: str, package: str, architecture: str) -> KernelReleases:
        target = self._select(target_id, package, architecture)
        coverage, data = await self._coverage(target, architecture)
        ordered = await asyncio.to_thread(self._versions, data, package, architecture)
        note = None if ordered else "선택한 커널 패키지와 아키텍처의 빌드 자료가 없습니다."
        status = "partial" if note and coverage.status == "ready" else coverage.status
        return KernelReleases(status, coverage.refreshing, coverage.sources, note, ordered)

    def _versions(self, data: tuple[KernelFeedData, ...], package: str, architecture: str) -> tuple[str, ...]:
        versions = {build.version for part in data for build in part.builds if build.package == package and build.architecture == architecture}
        return tuple(sorted(versions, key=cmp_to_key(self._source.compare_versions), reverse=True))

    async def upstream(self, target_id: str, search: str, page: int, page_size: int) -> UpstreamResults:
        target = next((target for target in self.targets if target.id == target_id and target.available), None)
        if target is None:
            raise ValueError("조회할 수 없는 배포판입니다.")
        if self._upstream is None:
            return UpstreamResults("error", False, None, None, page, page_size, ())
        (vendor, feeds), (linux, upstream_feeds) = await asyncio.gather(self._coverage(target), self._coverage(self._upstream))
        refreshing = vendor.refreshing or linux.refreshing
        as_of = max((s.refreshed_at for s in linux.sources if s.refreshed_at), default=None)
        if not feeds or not upstream_feeds:
            status = "error" if "error" in (vendor.status, linux.status) else "pending"
            return UpstreamResults(status, refreshing, as_of, None, page, page_size, ())
        status = "ready"
        if "partial" in (vendor.status, linux.status):
            status = "partial"
        elif "stale" in (vendor.status, linux.status):
            status = "stale"
        stamp = tuple((s.id, s.refreshed_at) for s in (*vendor.sources, *linux.sources))
        index = self._upstream_indexes.get(target.id)
        if index is None or index[0] != stamp:
            async with self._upstream_lock:
                index = self._upstream_indexes.get(target.id)
                if index is None or index[0] != stamp:
                    rows = await asyncio.to_thread(self._unlinked, feeds, upstream_feeds)
                    index = (stamp, rows)
                    self._upstream_indexes[target.id] = index
        ordered = index[1]
        query = search.strip().casefold()
        if query:
            ordered = tuple(item for item in ordered if query in item.cve_id.casefold() or query in item.title.casefold())
        start = (page - 1) * page_size
        return UpstreamResults(status, refreshing, as_of, len(ordered), page, page_size, ordered[start:start + page_size])

    @staticmethod
    def _unlinked(feeds: tuple[KernelFeedData, ...], upstream_feeds: tuple[KernelFeedData, ...]) -> tuple[UpstreamCve, ...]:
        linked = {item.cve_id for part in feeds for item in part.advisories}
        unlinked: dict[str, UpstreamCve] = {}
        for part in upstream_feeds:
            for item in part.advisories:
                if item.cve_id in linked or item.cve_id in unlinked:
                    continue
                unlinked[item.cve_id] = UpstreamCve(item.cve_id, item.title or item.cve_id, item.issued_at, item.advisory_url)
        return tuple(sorted(unlinked.values(), key=lambda item: (item.published_at or "", item.cve_id), reverse=True))

    async def find(self, target_id: str, build: KernelBuild, severity: str, search: str, page: int, page_size: int) -> KernelResults:
        target = self._select(target_id, build.package, build.architecture)
        self._source.validate(target, build)
        coverage, data = await self._coverage(target, build.architecture)
        has_builds = any(candidate.package == build.package and candidate.architecture == build.architecture
                         for part in data for candidate in part.builds)
        note = self._source.coverage_note(target, build, data) if has_builds else "선택한 커널 패키지와 아키텍처의 자료를 확인할 수 없습니다."
        status = "partial" if coverage.status == "ready" and note else coverage.status
        stamp = tuple((source.id, source.refreshed_at) for source in coverage.sources)
        cache_key = (target_id, build, stamp)
        if cache_key not in self._indexes:
            async with self._index_lock:
                if cache_key not in self._indexes:
                    self._indexes[cache_key] = await asyncio.to_thread(self._findings, target, build, data)
                    if len(self._indexes) > 8:
                        self._indexes.popitem(last=False)
        self._indexes.move_to_end(cache_key)
        findings = self._indexes[cache_key]
        evaluated = has_builds and (bool(findings) or note is None)
        query = search.casefold().strip()
        if query:
            findings = tuple(item for item in findings if self._contains(item, query))
        counts = {name: 0 for name in SEVERITIES}
        for item in findings:
            counts[item.severity] += 1
        filtered = [item for item in findings if severity == "all" or item.severity == severity]
        start = (page - 1) * page_size
        return KernelResults(status, coverage.refreshing, coverage.sources, note, len(filtered) if evaluated else None,
                             page, page_size, counts, tuple(filtered[start:start + page_size]))

    @staticmethod
    def _contains(item: KernelFinding, query: str) -> bool:
        if query in item.cve_id.casefold() or query in (item.summary or "").casefold():
            return True
        return any(query in text.casefold() for fix in item.fixes
                   for text in (fix.advisory_id, fix.title or "", fix.fixed_version))

    def _findings(self, target: KernelTarget, build: KernelBuild, data: tuple[KernelFeedData, ...]) -> tuple[KernelFinding, ...]:
        grouped: dict[str, list[KernelAdvisory]] = defaultdict(list)
        corrected: set[str] = set()
        for part in data:
            for item in part.advisories:
                if not self._source.same_branch(build, item):
                    continue
                if self._source.matches(target, build, item):
                    grouped[item.cve_id].append(item)
                else:
                    corrected.add(item.cve_id)
        findings = []
        for cve, evidence in grouped.items():
            if cve in corrected:
                continue
            severity = min((item.severity for item in evidence), key=SEVERITIES.index)
            fixes = {KernelFix(item.advisory_id, item.advisory_url, item.issued_at, item.fixed_version,
                               item.package, item.architecture, item.title or None) for item in evidence}
            ordered = sorted(fixes, key=lambda fix: (fix.issued_at or "", fix.advisory_id, fix.fixed_version,
                                                      fix.package, fix.architecture, fix.advisory_url), reverse=True)
            summary = next((item.summary for item in evidence if item.summary), None)
            findings.append(KernelFinding(cve, severity, summary, tuple(ordered)))
        return tuple(sorted(findings, key=lambda item: (SEVERITIES.index(item.severity), item.cve_id)))
