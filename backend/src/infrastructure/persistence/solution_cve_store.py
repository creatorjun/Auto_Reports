# backend/src/infrastructure/persistence/solution_cve_store.py
from src.domain.entities.solution_package import SolutionFeedData
from src.infrastructure.persistence.advisory_feed_store import SqliteAdvisorySnapshotStore


class SqliteSolutionSnapshotStore(SqliteAdvisorySnapshotStore[SolutionFeedData]):
    def __init__(self, path: str) -> None:
        super().__init__(path, "solution", self._decode_data)

    @staticmethod
    def _decode_data(data: dict) -> SolutionFeedData:
        matches = {key: tuple(ids) if ids is not None else None for key, ids in data["matches"].items()}
        return SolutionFeedData(data["ecosystem"], matches)
