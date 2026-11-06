# backend/src/infrastructure/external/kernel_cve_source.py
import httpx

from src.domain.entities.kernel_cve import KernelFeed, KernelFeedData, KernelTarget
from src.infrastructure.external.el_kernel_cve import OTHER_TARGETS, fetch_other
from src.infrastructure.external.kernel_rpm import compare_versions, coverage_note, matches_build, same_branch, validate_build
from src.infrastructure.external.kernel_upstream import UPSTREAM_TARGET, fetch_upstream
from src.infrastructure.external.oracle_kernel_cve import ORACLE_TARGETS, fetch_oracle


class KernelCveSource:
    targets = (*ORACLE_TARGETS, *OTHER_TARGETS, UPSTREAM_TARGET)
    validate = staticmethod(validate_build)
    matches = staticmethod(matches_build)
    same_branch = staticmethod(same_branch)
    compare_versions = staticmethod(compare_versions)
    coverage_note = staticmethod(coverage_note)

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
        self._owns_client = client is None

    async def fetch(self, target: KernelTarget, feed: KernelFeed) -> KernelFeedData:
        if target not in self.targets or not target.available or feed not in target.feeds:
            raise ValueError("지원하지 않는 커널 권고 출처입니다.")
        if target in ORACLE_TARGETS:
            return await fetch_oracle(self._client, target, feed)
        if target == UPSTREAM_TARGET:
            return await fetch_upstream(self._client)
        return await fetch_other(self._client, target, feed)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
