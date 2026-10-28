# backend/src/infrastructure/persistence/cve_inventory_snapshot_store.py
import asyncio
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from src.application.ports.cve_inventory_port import CveInventorySnapshotPort
from src.domain.entities.cve_inventory import CveFinding, CvePackageSnapshot, CveStoredSnapshot, CveVersionRange


def decode_snapshot(payload: str) -> CveStoredSnapshot:
    document = json.loads(payload)
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported CVE snapshot version")
    value = document["snapshot"]
    packages = []
    for entry in value["packages"]:
        raw = dict(entry)
        findings = []
        for item in raw["findings"]:
            finding = dict(item)
            for name in ("affected_versions", "fixed_versions", "references", "source_ids", "affected_inventory_versions"):
                finding[name] = tuple(finding.get(name, ()))
            finding["ranges"] = tuple(CveVersionRange(**range_value) for range_value in finding.get("ranges", ()))
            findings.append(CveFinding(**finding))
        raw["findings"] = tuple(findings)
        raw["first_seen"] = tuple(tuple(item) for item in raw.get("first_seen", ()))
        packages.append(CvePackageSnapshot(**raw))
    return CveStoredSnapshot(
        dataset_id=value["dataset_id"], packages=tuple(packages),
        last_attempt_at=value.get("last_attempt_at"), refreshed_at=value.get("refreshed_at"),
        initialized=bool(value.get("initialized", False)),
    )


class SqliteCveInventorySnapshotStore(CveInventorySnapshotPort):
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._closed = False

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("CVE snapshot store is closed")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("CREATE TABLE IF NOT EXISTS cve_inventory_snapshot (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL)")
        return connection

    async def _call(self, function, *args):
        task = asyncio.create_task(asyncio.to_thread(function, *args))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                await task
            except Exception:
                pass
            raise

    async def load(self) -> CveStoredSnapshot | None:
        return await self._call(self._load)

    def _load(self) -> CveStoredSnapshot | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT payload FROM cve_inventory_snapshot WHERE id=1").fetchone()
            return decode_snapshot(row[0]) if row else None
        finally:
            connection.close()

    async def save(self, snapshot: CveStoredSnapshot) -> None:
        await self._call(self._save, snapshot)

    def _save(self, snapshot: CveStoredSnapshot) -> None:
        payload = json.dumps({"schema_version": 1, "snapshot": asdict(snapshot)}, ensure_ascii=False, separators=(",", ":"))
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO cve_inventory_snapshot (id,payload) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                    (payload,),
                )
        finally:
            connection.close()

    async def aclose(self) -> None:
        self._closed = True
