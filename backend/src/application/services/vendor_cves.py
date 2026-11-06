# backend/src/application/services/vendor_cves.py
import asyncio
from collections import OrderedDict, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from datetime import datetime
from functools import cmp_to_key
from typing import Generic, TypeVar

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.application.services.daily_advisories import AdvisoryCoverage, DailyAdvisories, FeedT, TargetT
from src.domain.entities.advisory_feed import AdvisorySeverity, DataT, SEVERITIES


BuildT = TypeVar("BuildT")


@dataclass(frozen=True)
class VendorReleases(AdvisoryCoverage, Generic[BuildT]):
    versions: tuple[BuildT, ...]


@dataclass(frozen=True)
class VendorEvidence:
    advisory_id: str
    advisory_url: str
    issued_at: str | None
    affected_through: str | None
    affected_version: str | None
    fixed_version: str | None
    title: str | None
    component: str | None
    cvss_score: float | None
    channel: str | None

    @classmethod
    def from_record(cls, item, **extra):
        return cls(item.advisory_id, item.advisory_url, item.issued_at, item.affected_through,
                   item.affected_version, item.fixed_version, item.title or None, item.component or None,
                   item.cvss_score, item.channel or None, **extra)

    def contains(self, query: str) -> bool:
        return any(query in (value or "").casefold() for value in (
            self.advisory_id, self.title, self.component, self.affected_version,
            self.affected_through, self.fixed_version, self.channel,
        ))


EvidenceT = TypeVar("EvidenceT", bound=VendorEvidence)


@dataclass(frozen=True)
class VendorFinding(Generic[EvidenceT]):
    cve_id: str
    severity: AdvisorySeverity
    summary: str | None
    fixes: tuple[EvidenceT, ...]


@dataclass(frozen=True)
class VendorResults(AdvisoryCoverage, Generic[EvidenceT]):
    total: int | None
    page: int
    page_size: int
    severity_counts: dict[str, int]
    items: tuple[VendorFinding[EvidenceT], ...]


class VendorCves(DailyAdvisories[TargetT, FeedT, DataT], Generic[TargetT, FeedT, DataT, BuildT, EvidenceT]):
    def __init__(
        self, source, store: AdvisorySnapshotPort[DataT], clock: Callable[[], datetime] | None, *,
        product: str, evidence: Callable[..., EvidenceT],
    ) -> None:
        super().__init__(source.targets, source.fetch, store, clock)
        self._product = product
        self._evidence = evidence
        self._source = source
        self.targets = source.targets
        self._index_lock = asyncio.Lock()
        self._indexes: OrderedDict[tuple, tuple[str | None, tuple[VendorFinding[EvidenceT], ...]]] = OrderedDict()

    def _select(self, target_id: str) -> TargetT:
        target = next((item for item in self.targets if item.id == target_id and item.available), None)
        if target is None:
            raise ValueError(f"조회할 수 없는 {self._product}입니다.")
        return target

    async def releases(self, target_id: str) -> VendorReleases[BuildT]:
        target = self._select(target_id)
        coverage, data = await self.read_coverage(target, target.feeds)
        versions = await asyncio.to_thread(self._versions, target, data)
        note = None if versions else f"선택한 {self._product}의 버전 자료를 확인할 수 없습니다."
        status = "partial" if note and coverage.status == "ready" else coverage.status
        return VendorReleases(status, coverage.refreshing, coverage.sources, note, versions)

    def _versions(self, target: TargetT, data: tuple[DataT, ...]) -> tuple[BuildT, ...]:
        versions: dict[str, BuildT] = {}
        for part in data:
            for build in part.builds:
                previous = versions.get(build.version)
                if previous is None:
                    versions[build.version] = build
                    continue
                preferred = max((previous, build), key=lambda item: (item.issued_at or "", bool(item.channel), bool(item.label)))
                other = previous if preferred is build else build
                missing = {
                    field.name: getattr(other, field.name) for field in fields(preferred)
                    if getattr(preferred, field.name) in (None, "") and getattr(other, field.name) not in (None, "")
                }
                versions[build.version] = replace(preferred, **missing) if missing else preferred
        compare = cmp_to_key(lambda a, b: self._source.compare_versions(target, a.version, b.version))
        return tuple(build if build.label else replace(build, label=build.version)
                     for build in sorted(versions.values(), key=compare, reverse=True))

    async def find(self, target_id: str, version: str, severity: str, search: str, page: int, page_size: int) -> VendorResults[EvidenceT]:
        target = self._select(target_id)
        self._source.validate(target, version)
        coverage, data = await self.read_coverage(target, target.feeds)
        risks = {feed.id for feed in target.feeds if not feed.releases_only}
        risk_sources = [source for source in coverage.sources if source.id in risks]
        counts = dict.fromkeys(SEVERITIES, 0)
        if not any(source.refreshed_at is not None for source in risk_sources):
            status = "pending" if any(s.status == "pending" for s in risk_sources) else "error"
            return VendorResults(status, coverage.refreshing, coverage.sources, f"선택한 {self._product}의 취약점 권고를 확인할 수 없습니다.",
                               None, page, page_size, counts, ())
        stamp = tuple((source.id, source.refreshed_at) for source in coverage.sources)
        cache_key = (target_id, version, stamp)
        if cache_key not in self._indexes:
            async with self._index_lock:
                if cache_key not in self._indexes:
                    self._indexes[cache_key] = await asyncio.to_thread(self._findings, target, version, data)
                    if len(self._indexes) > 16:
                        self._indexes.popitem(last=False)
        self._indexes.move_to_end(cache_key)
        note, all_findings = self._indexes[cache_key]
        status = "partial" if note and coverage.status == "ready" else coverage.status
        query = search.strip().casefold()
        filtered = []
        for item in all_findings:
            if query and not self._contains(item, query):
                continue
            counts[item.severity] += 1
            if severity == "all" or severity == item.severity:
                filtered.append(item)
        total = len(filtered) if all_findings or note is None else None
        start = (page - 1) * page_size
        return VendorResults(status, coverage.refreshing, coverage.sources, note, total, page, page_size, counts,
                           tuple(filtered[start:start + page_size]))

    def _findings(self, target: TargetT, version: str, data: tuple[DataT, ...]) -> tuple[str | None, tuple[VendorFinding[EvidenceT], ...]]:
        note = self._source.coverage_note(target, version, data)
        matches = self._source.matcher(target, version, data)
        if matches is None:
            return note or "선택한 빌드의 적용 범위를 공급사 자료에서 확인할 수 없습니다.", ()
        grouped = defaultdict(list)
        for part in data:
            for item in part.advisories:
                if matches(item):
                    grouped[item.cve_id].append(item)
        findings = []
        for cve, evidence in grouped.items():
            severity = min((item.severity for item in evidence), key=SEVERITIES.index)
            fixes = tuple(dict.fromkeys(self._evidence(item) for item in evidence))
            ordered = sorted(fixes, key=lambda fix: (fix.issued_at or "", fix.advisory_id), reverse=True)
            summary = next((item.summary for item in evidence if item.summary), None)
            findings.append(VendorFinding(cve, severity, summary, tuple(ordered)))
        return note, tuple(sorted(findings, key=lambda item: (SEVERITIES.index(item.severity), item.cve_id)))

    @staticmethod
    def _contains(item: VendorFinding[EvidenceT], query: str) -> bool:
        if query in item.cve_id.casefold() or query in (item.summary or "").casefold():
            return True
        return any(fix.contains(query) for fix in item.fixes)
