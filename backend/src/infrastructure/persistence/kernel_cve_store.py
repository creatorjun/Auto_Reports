# backend/src/infrastructure/persistence/kernel_cve_store.py
from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeedData
from src.infrastructure.persistence.advisory_feed_store import SqliteAdvisorySnapshotStore


class SqliteKernelSnapshotStore(SqliteAdvisorySnapshotStore[KernelFeedData]):
    def __init__(self, path: str) -> None:
        super().__init__(path, "kernel", self._decode_data)

    @staticmethod
    def _decode_data(data: dict) -> KernelFeedData:
        return KernelFeedData(
            advisories=tuple(KernelAdvisory(**item) for item in data["advisories"]),
            builds=tuple(KernelBuild(**item) for item in data["builds"]),
            complete=data["complete"], note=data["note"],
        )
