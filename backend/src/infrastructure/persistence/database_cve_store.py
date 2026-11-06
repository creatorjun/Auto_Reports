# backend/src/infrastructure/persistence/database_cve_store.py
from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeedData
from src.infrastructure.persistence.advisory_feed_store import SqliteAdvisorySnapshotStore


class SqliteDatabaseSnapshotStore(SqliteAdvisorySnapshotStore[DatabaseFeedData]):
    def __init__(self, path: str) -> None:
        super().__init__(path, "database", self._decode_data)

    @staticmethod
    def _decode_data(data: dict) -> DatabaseFeedData:
        return DatabaseFeedData(tuple(DatabaseAdvisory(**item) for item in data["advisories"]),
                                tuple(DatabaseBuild(**item) for item in data["builds"]), data["complete"], data["note"])
