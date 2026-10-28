# backend/src/application/use_cases/cve_inventory.py
import asyncio
import logging
import math
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from src.application.ports.cve_inventory_port import CveInventoryLoaderPort, CveInventorySnapshotPort, CvePackageSourcePort
from src.domain.entities.cve_inventory import CveInventory, CveInventoryPackage, CvePackageSnapshot, CveStoredSnapshot


logger = logging.getLogger(__name__)
SEVERITIES = ("critical", "high", "medium", "low", "unknown")


class CveRefreshThrottled(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("CVE 수집은 2시간 간격으로 실행됩니다. 저장된 결과를 먼저 확인해 주세요.")


class CveInventoryUseCase:
    def __init__(
        self, loader: CveInventoryLoaderPort, source: CvePackageSourcePort,
        store: CveInventorySnapshotPort | None = None, *,
        clock: Callable[[], datetime] | None = None, refresh_interval_seconds: int = 7200,
        concurrency: int = 4,
    ) -> None:
        self._loader = loader
        self._source = source
        self._store = store
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._interval = max(60, refresh_interval_seconds)
        self._concurrency = max(1, min(6, concurrency))
        self._inventory = CveInventory("", None, (), 0, 0)
        self._states: dict[str, CvePackageSnapshot] = {}
        self._last_attempt: datetime | None = None
        self._refreshed_at: str | None = None
        self._initialized = False
        self._loaded = False
        self._closed = False
        self._error: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._persist_lock = asyncio.Lock()
        self._completed = 0
        self._total = 0
        self._rows: tuple[dict, ...] | None = None
        self._last_checkpoint = 0.0

    def _running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("CVE inventory service is closed")

    @staticmethod
    def _carry_package_state(state: CvePackageSnapshot) -> CvePackageSnapshot:
        return replace(
            state,
            findings=tuple(replace(finding, inventory_impact="unknown", affected_inventory_versions=()) for finding in state.findings),
            status="stale" if state.last_success_at is not None else "pending",
            error=None,
        )

    async def _load_inventory(self) -> bool:
        try:
            inventory = await self._loader.load()
            await self._source.configure(inventory.packages)
        except Exception as error:
            logger.warning("CVE inventory load failed: %s", type(error).__name__)
            self._error = "패키지 인벤토리를 읽지 못했습니다. 인벤토리 파일 설정을 확인해 주세요."
            return False
        changed = inventory.dataset_id != self._inventory.dataset_id
        self._inventory = inventory
        if changed:
            self._states = {
                package.id: (
                    self._carry_package_state(self._states[package.id])
                    if package.mapping_status == "ready" and package.id in self._states
                    else CvePackageSnapshot(package.id, status="pending" if package.mapping_status == "ready" else "unmapped")
                )
                for package in inventory.packages
            }
            self._last_attempt = None
            self._refreshed_at = None
            self._initialized = False
            self._rows = None
        self._error = None
        return True

    async def initialize(self) -> None:
        async with self._lock:
            self._ensure_open()
            if self._loaded:
                return
            loaded = await self._load_inventory()
            if loaded and self._store is not None:
                try:
                    saved = await self._store.load()
                    if saved is not None:
                        same_dataset = saved.dataset_id == self._inventory.dataset_id
                        for state in saved.packages:
                            if state.package_id in self._states and self._states[state.package_id].status != "unmapped":
                                self._states[state.package_id] = state if same_dataset else self._carry_package_state(state)
                        if same_dataset:
                            self._last_attempt = datetime.fromisoformat(saved.last_attempt_at) if saved.last_attempt_at else None
                            if self._last_attempt is not None and self._last_attempt.tzinfo is None:
                                raise ValueError("Snapshot timestamp needs timezone")
                            self._refreshed_at = saved.refreshed_at
                            self._initialized = saved.initialized
                except Exception as error:
                    logger.warning("CVE inventory snapshot restore failed: %s", type(error).__name__)
                    self._error = "저장된 CVE 결과를 복원하지 못했습니다. 새로 수집해 주세요."
            self._loaded = True

    def _retry_after(self) -> int:
        if self._last_attempt is None:
            return 0
        return max(0, math.ceil(self._interval - (self._clock() - self._last_attempt).total_seconds()))

    async def _request_refresh(self, *, scheduled: bool = False, initial: bool = False) -> None:
        await self.initialize()
        async with self._lock:
            self._ensure_open()
            if self._running():
                return
            if not await self._load_inventory():
                return
            retry = self._retry_after()
            if retry and not (scheduled and not initial and retry <= 5):
                if not scheduled:
                    raise CveRefreshThrottled(retry)
                return
            self._last_attempt = self._clock()
            self._completed = 0
            self._total = sum(package.mapping_status == "ready" for package in self._inventory.packages)
            self._task = asyncio.create_task(self._refresh(), name="cve-inventory-refresh")

    async def start_if_needed(self) -> None:
        await self._request_refresh(scheduled=True, initial=True)

    async def refresh_scheduled(self) -> None:
        await self._request_refresh(scheduled=True)
        if self._task is not None:
            await asyncio.shield(self._task)

    async def _persist(self, *, force: bool = True) -> None:
        if self._store is None:
            return
        async with self._persist_lock:
            if not force and time.monotonic() - self._last_checkpoint < 60:
                return
            try:
                await self._store.save(CveStoredSnapshot(
                    dataset_id=self._inventory.dataset_id, packages=tuple(self._states.values()),
                    last_attempt_at=self._last_attempt.isoformat() if self._last_attempt else None,
                    refreshed_at=self._refreshed_at, initialized=self._initialized,
                ))
                self._last_checkpoint = time.monotonic()
            except Exception as error:
                logger.warning("CVE inventory snapshot save failed: %s", type(error).__name__)
                self._error = "CVE 결과 저장에 실패했습니다. 현재 표시 결과는 재시작 후 유지되지 않을 수 있습니다."

    async def _refresh_package(self, package: CveInventoryPackage, semaphore: asyncio.Semaphore, exploited: frozenset[str] | None) -> None:
        async with semaphore:
            previous = self._states[package.id]
            attempted = self._clock().isoformat()
            self._states[package.id] = replace(previous, last_attempt_at=attempted)
            try:
                findings = await self._source.fetch(package)
                existing = {finding.cve_id: finding for finding in previous.findings}
                observed = self._clock().isoformat()
                history = dict(previous.first_seen)
                for finding in previous.findings:
                    history.setdefault(finding.cve_id, finding.first_seen_at or observed)
                collected = []
                for finding in findings:
                    first_seen = history.setdefault(finding.cve_id, observed)
                    collected.append(replace(
                        finding, first_seen_at=first_seen,
                        known_exploited=(finding.cve_id in exploited) if exploited is not None else (
                            finding.known_exploited or (finding.cve_id in existing and existing[finding.cve_id].known_exploited)
                        ),
                    ))
                findings = tuple(collected)
                self._states[package.id] = CvePackageSnapshot(
                    package.id, findings, "ok", observed, attempted, first_seen=tuple(sorted(history.items())),
                )
            except Exception as error:
                logger.warning("CVE package collection failed for %s: %s", package.id, type(error).__name__)
                self._states[package.id] = replace(
                    previous, status="stale" if previous.last_success_at else "error", last_attempt_at=attempted,
                    error="조회에 실패했습니다. 이전 결과가 있으면 유지합니다.",
                )
            self._rows = None
            self._completed += 1
            await self._persist(force=False)

    async def _refresh(self) -> None:
        await self._persist()
        try:
            try:
                exploited = await self._source.begin_refresh()
            except Exception as error:
                logger.warning("CVE supplemental source failed: %s", type(error).__name__)
                exploited = None
            semaphore = asyncio.Semaphore(self._concurrency)
            await asyncio.gather(*(
                self._refresh_package(package, semaphore, exploited)
                for package in self._inventory.packages if package.mapping_status == "ready"
            ))
            self._initialized = True
            self._refreshed_at = self._clock().isoformat()
        finally:
            await self._persist()

    def _all_rows(self) -> tuple[dict, ...]:
        if self._rows is None:
            rows = []
            for package in self._inventory.packages:
                state = self._states.get(package.id, CvePackageSnapshot(package.id))
                for finding in state.findings:
                    rows.append({
                        **finding.__dict__, "id": f"{package.id}:{finding.cve_id}", "package_id": package.id,
                        "package_name": package.name, "ecosystem": package.ecosystem,
                        "inventory_versions": package.versions, "product_names": package.product_names,
                        "categories": package.categories, "source": package.source, "collection_status": state.status,
                    })
            self._rows = tuple(rows)
        return self._rows

    async def get_snapshot(
        self, *, refresh: bool = False, severity: str = "all", search: str = "", ecosystem: str = "all",
        impact: str = "all", page: int = 1, page_size: int = 50, sort: str = "severity",
    ) -> dict:
        await self.initialize()
        if refresh:
            await self._request_refresh()
        rows = self._all_rows()
        terms = search.casefold().strip()
        selected = [row for row in rows if
            (severity == "all" or row["severity"] == severity)
            and (ecosystem == "all" or row["ecosystem"] == ecosystem)
            and (impact == "all" or row["inventory_impact"] == impact)
            and (not terms or terms in " ".join((row["package_name"], row["cve_id"], row["title"], *row["product_names"], *row["affected_versions"], *row["fixed_versions"])).casefold())
        ]
        if sort == "package":
            selected.sort(key=lambda row: (row["package_name"].casefold(), row["cve_id"]))
        elif sort in {"published", "modified", "newest"}:
            key = "first_seen_at" if sort == "newest" else f"{sort}_at"
            selected.sort(key=lambda row: (row.get(key) or "", row["cve_id"]), reverse=True)
        else:
            selected.sort(key=lambda row: (-SEVERITIES.index(row["severity"]), row["cvss_score"] or 0, row["published_at"] or "", row["cve_id"]), reverse=True)
        counts = Counter(row["severity"] for row in rows)
        status_counts = Counter(state.status for state in self._states.values())
        coverage = {name: status_counts.get(name, 0) for name in ("unmapped", "ok", "stale", "error", "pending")}
        coverage.update(total=len(self._inventory.packages), ready=len(self._inventory.packages) - coverage["unmapped"])
        offset = (page - 1) * page_size
        return {
            "items": [{**row, "ranges": [asdict(value) for value in row["ranges"]]} for row in selected[offset:offset + page_size]],
            "total": len(selected), "page": page, "page_size": page_size,
            "severity_counts": {severity: counts.get(severity, 0) for severity in SEVERITIES},
            "inventory": {
                "dataset_id": self._inventory.dataset_id, "snapshot_at": self._inventory.snapshot_at,
                "product_count": self._inventory.product_count, "target_count": self._inventory.target_count,
                "package_count": len(self._inventory.packages), "runtime_verified": self._inventory.runtime_verified,
            },
            "coverage": coverage, "ecosystems": sorted({package.ecosystem for package in self._inventory.packages}),
            "initialized": self._initialized, "refreshing": self._running(), "refreshed_at": self._refreshed_at,
            "next_refresh_at": (self._last_attempt + timedelta(seconds=self._interval)).isoformat() if self._last_attempt else None,
            "retry_after_seconds": self._retry_after(), "refresh_interval_seconds": self._interval,
            "progress": {"completed": self._completed, "total": self._total}, "error": self._error,
        }

    async def get_packages(self, *, search: str = "", status: str = "all", page: int = 1, page_size: int = 50) -> dict:
        await self.initialize()
        terms = search.casefold().strip()
        items = []
        for package in self._inventory.packages:
            state = self._states.get(package.id, CvePackageSnapshot(package.id))
            if status != "all" and state.status != status:
                continue
            if terms and terms not in " ".join((package.name, package.ecosystem, *package.product_names)).casefold():
                continue
            items.append({
                "id": package.id, "name": package.name, "ecosystem": package.ecosystem, "versions": package.versions,
                "product_names": package.product_names, "categories": package.categories, "source": package.source,
                "mapping_status": package.mapping_status, "mapping_reason": package.mapping_reason,
                "status": state.status, "last_success_at": state.last_success_at, "last_attempt_at": state.last_attempt_at,
                "error": state.error, "cve_count": len(state.findings),
            })
        items.sort(key=lambda item: (item["name"].casefold(), item["id"]))
        offset = (page - 1) * page_size
        return {"items": items[offset:offset + page_size], "total": len(items), "page": page, "page_size": page_size}

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
