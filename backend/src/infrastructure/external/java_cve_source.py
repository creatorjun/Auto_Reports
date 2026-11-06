# backend/src/infrastructure/external/java_cve_source.py
import httpx

from src.domain.entities.java_cve import JavaFeed, JavaFeedData, JavaTarget
from src.infrastructure.external.java_openjdk import OPENJDK_TARGET, fetch_openjdk, openjdk_coverage_note, openjdk_matcher
from src.infrastructure.external.java_version import compare_java_versions, java_version
from src.infrastructure.external.java_zulu import ZULU_TARGET, compare_zulu_versions, fetch_zulu, validate_zulu, zulu_coverage_note, zulu_matcher


class JavaCveSource:
    targets = (OPENJDK_TARGET, ZULU_TARGET)

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=45, follow_redirects=False)
        self._owns_client = client is None

    async def fetch(self, target: JavaTarget, feed: JavaFeed) -> JavaFeedData:
        if target not in self.targets or feed not in target.feeds:
            raise ValueError("지원하지 않는 Java 권고 출처입니다.")
        if target == OPENJDK_TARGET:
            return await fetch_openjdk(self._client, target, feed)
        return await fetch_zulu(self._client, target, feed)

    def validate(self, target: JavaTarget, version: str) -> None:
        if target == OPENJDK_TARGET:
            java_version(version)
        else:
            validate_zulu(version)

    def matcher(self, target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]):
        if target == OPENJDK_TARGET:
            return openjdk_matcher(version, data)
        return zulu_matcher(target, version, data)

    def coverage_note(self, target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]) -> str | None:
        if target == OPENJDK_TARGET:
            return openjdk_coverage_note(version, data)
        return zulu_coverage_note(target, version, data)

    def compare_versions(self, target: JavaTarget, left: str, right: str) -> int:
        if target == OPENJDK_TARGET:
            return compare_java_versions(left, right)
        return compare_zulu_versions(left, right)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
