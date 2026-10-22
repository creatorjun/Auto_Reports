# backend/src/infrastructure/persistence/security_news_snapshot_store.py
import asyncio
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from src.application.ports.security_news_snapshot_port import SecurityNewsSnapshotPort
from src.domain.entities.security_news import (
    SecurityCveRemediation,
    SecurityNewsItem,
    SecurityNewsSourceResult,
    SecurityNewsSourceState,
    SecurityNewsStoredSnapshot,
)


def _encode(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError("Unsupported security news snapshot value")


def _datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Security news snapshot timestamps must include timezone")
    return result


def _decode(payload: str) -> SecurityNewsStoredSnapshot:
    document = json.loads(payload)
    if document["version"] != 1:
        raise ValueError("Unsupported security news snapshot version")
    value = document["snapshot"]
    results = []
    for source_id, result in value["results"]:
        items = []
        for raw in result["items"]:
            item = dict(raw)
            item["published_at"] = _datetime(item.get("published_at"))
            item["updated_at"] = _datetime(item.get("updated_at"))
            item["cve_ids"] = tuple(item.get("cve_ids", ()))
            item["remediations"] = tuple(SecurityCveRemediation(**value) for value in item.get("remediations", ()))
            items.append(SecurityNewsItem(**item))
        results.append((source_id, SecurityNewsSourceResult(
            tuple(items), frozenset(result["known_exploited_cve_ids"]), result.get("warning"),
        )))
    sources = []
    for raw in value["sources"]:
        state = dict(raw)
        state["last_success_at"] = _datetime(state.get("last_success_at"))
        sources.append(SecurityNewsSourceState(**state))
    attempts = []
    for source_id, timestamp in value["source_attempts"]:
        parsed = _datetime(timestamp)
        if parsed is None:
            raise ValueError("Security news source attempt timestamp is missing")
        attempts.append((source_id, parsed))
    return SecurityNewsStoredSnapshot(
        results=tuple(results), sources=tuple(sources), source_attempts=tuple(attempts),
        last_attempt=_datetime(value["last_attempt"]),
        refreshed_at=_datetime(value["refreshed_at"]), initialized=value["initialized"],
    )


class SqliteSecurityNewsSnapshotStore(SecurityNewsSnapshotPort):
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._closed = False

    @contextmanager
    def _connection(self):
        if self._closed:
            raise RuntimeError("Security news snapshot store is closed")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS news_snapshot (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS news_schedule (id INTEGER PRIMARY KEY CHECK (id=1), last_day TEXT NOT NULL);"
            )
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

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

    async def load(self) -> SecurityNewsStoredSnapshot | None:
        return await self._call(self._load)

    def _load(self) -> SecurityNewsStoredSnapshot | None:
        with self._connection() as connection:
            row = connection.execute("SELECT payload FROM news_snapshot WHERE id=1").fetchone()
        return _decode(row[0]) if row is not None else None

    async def save(self, snapshot: SecurityNewsStoredSnapshot) -> None:
        await self._call(self._save, snapshot)

    def _save(self, snapshot: SecurityNewsStoredSnapshot) -> None:
        payload = json.dumps({"version": 1, "snapshot": asdict(snapshot)}, ensure_ascii=False, default=_encode)
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO news_snapshot (id,payload) VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (payload,),
            )

    async def claim_daily_refresh(self, day: date) -> bool:
        return await self._call(self._claim_daily_refresh, day)

    def _claim_daily_refresh(self, day: date) -> bool:
        with self._connection() as connection:
            result = connection.execute(
                "INSERT INTO news_schedule (id,last_day) VALUES (1,?) "
                "ON CONFLICT(id) DO UPDATE SET last_day=excluded.last_day "
                "WHERE news_schedule.last_day < excluded.last_day",
                (day.isoformat(),),
            )
            return result.rowcount == 1

    async def aclose(self) -> None:
        self._closed = True
