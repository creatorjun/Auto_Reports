# backend/src/infrastructure/external/database_cve_source.py
import httpx

from src.domain.entities.database_cve import DatabaseFeed, DatabaseFeedData, DatabaseTarget
from src.infrastructure.external.database_mariadb import MARIADB_TARGET, fetch_mariadb
from src.infrastructure.external.database_mysql import MYSQL_TARGET, fetch_mysql
from src.infrastructure.external.database_postgresql import POSTGRESQL_TARGET, fetch_postgresql
from src.infrastructure.external.database_version import compare_versions, coverage_note, matcher, validate_version


class DatabaseCveSource:
    targets = (MARIADB_TARGET, MYSQL_TARGET, POSTGRESQL_TARGET)

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
        self._owns_client = client is None

    async def fetch(self, target: DatabaseTarget, feed: DatabaseFeed) -> DatabaseFeedData:
        if target not in self.targets or feed not in target.feeds:
            raise ValueError("지원하지 않는 데이터베이스 권고 출처입니다.")
        fetch = {MARIADB_TARGET.id: fetch_mariadb, MYSQL_TARGET.id: fetch_mysql, POSTGRESQL_TARGET.id: fetch_postgresql}
        return await fetch[target.id](self._client, target, feed)

    def validate(self, target, version):
        validate_version(target.id, version)

    def matcher(self, target, version, data):
        return matcher(target.id, version, data)

    def coverage_note(self, target, version, data):
        return coverage_note(target.id, version, data)

    def compare_versions(self, target, left, right):
        return compare_versions(left, right)

    async def aclose(self):
        if self._owns_client:
            await self._client.aclose()
