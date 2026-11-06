# backend/src/application/use_cases/database_cves.py
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.application.ports.database_cve_port import DatabaseCvePort
from src.application.services.vendor_cves import VendorCves, VendorEvidence, VendorReleases, VendorResults
from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeed, DatabaseFeedData, DatabaseTarget


@dataclass(frozen=True)
class DatabaseEvidence(VendorEvidence):
    series: str
    affected_from: str | None
    affected_from_inclusive: bool
    affected_through_inclusive: bool

    @classmethod
    def from_advisory(cls, item: DatabaseAdvisory):
        return cls.from_record(item, series=item.series, affected_from=item.affected_from,
                               affected_from_inclusive=item.affected_from_inclusive,
                               affected_through_inclusive=item.affected_through_inclusive)

    def contains(self, query: str) -> bool:
        return super().contains(query) or query in (self.affected_from or "").casefold() or query in self.series.casefold()


DatabaseReleases = VendorReleases[DatabaseBuild]
DatabaseResults = VendorResults[DatabaseEvidence]


class DatabaseCveUseCase(VendorCves[DatabaseTarget, DatabaseFeed, DatabaseFeedData, DatabaseBuild, DatabaseEvidence]):
    def __init__(
        self, source: DatabaseCvePort, store: AdvisorySnapshotPort[DatabaseFeedData], clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(source, store, clock, product="데이터베이스 제품", evidence=DatabaseEvidence.from_advisory)
