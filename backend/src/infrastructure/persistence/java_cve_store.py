# backend/src/infrastructure/persistence/java_cve_store.py
from src.domain.entities.java_cve import JavaAdvisory, JavaBuild, JavaFeedData
from src.infrastructure.persistence.advisory_feed_store import SqliteAdvisorySnapshotStore


class SqliteJavaSnapshotStore(SqliteAdvisorySnapshotStore[JavaFeedData]):
    def __init__(self, path: str) -> None:
        super().__init__(path, "java", self._decode_data)

    @staticmethod
    def _decode_data(data: dict) -> JavaFeedData:
        return JavaFeedData(tuple(JavaAdvisory(**item) for item in data["advisories"]),
                            tuple(JavaBuild(**item) for item in data["builds"]), data["complete"], data["note"])
