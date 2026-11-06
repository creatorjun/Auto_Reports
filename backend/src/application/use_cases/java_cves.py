# backend/src/application/use_cases/java_cves.py
from collections.abc import Callable
from datetime import datetime

from src.application.ports.advisory_feed_port import AdvisorySnapshotPort
from src.application.ports.java_cve_port import JavaCvePort
from src.application.services.vendor_cves import VendorCves, VendorEvidence, VendorReleases, VendorResults
from src.domain.entities.java_cve import JavaBuild, JavaFeed, JavaFeedData, JavaTarget


JavaReleases = VendorReleases[JavaBuild]
JavaResults = VendorResults[VendorEvidence]


class JavaCveUseCase(VendorCves[JavaTarget, JavaFeed, JavaFeedData, JavaBuild, VendorEvidence]):
    def __init__(
        self, source: JavaCvePort, store: AdvisorySnapshotPort[JavaFeedData], clock: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(source, store, clock, product="Java 배포판", evidence=VendorEvidence.from_record)
