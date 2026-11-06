# backend/src/infrastructure/persistence/advisory_feed_store.py
import asyncio
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import zlib
from typing import Generic, Literal

from src.domain.entities.advisory_feed import AdvisorySnapshot, DataT, FeedClaim, FeedHistory


class SqliteAdvisorySnapshotStore(Generic[DataT]):
    def __init__(self, path: str, kind: Literal["kernel", "java", "database"], decode: Callable[[dict], DataT]) -> None:
        self._path = Path(path)
        self._decode_payload = decode
        if kind not in {"kernel", "java", "database"}:
            raise ValueError("Unknown advisory database kind")
        self._snapshots = kind + "_feed_v1"
        self._attempts = kind + "_feed_attempt"

    def _connect(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self._path, timeout=15)
        db.execute(f"CREATE TABLE IF NOT EXISTS {self._snapshots} ("
                   "target TEXT NOT NULL, feed TEXT NOT NULL, refreshed_at TEXT NOT NULL, "
                   "payload BLOB NOT NULL, PRIMARY KEY(target, feed))")
        db.execute(f"CREATE TABLE IF NOT EXISTS {self._attempts} (target TEXT NOT NULL, feed TEXT NOT NULL, "
                   "day TEXT NOT NULL, owner TEXT, lease_until TEXT, error TEXT, PRIMARY KEY(target,feed))")
        return db

    async def load(self, target: str, feed: str) -> FeedHistory[DataT]:
        return await asyncio.to_thread(self._load, target, feed)

    def _load(self, target: str, feed: str) -> FeedHistory[DataT]:
        with closing(self._connect()) as db, db:
            db.execute("BEGIN")
            attempt = db.execute(f"SELECT day,error FROM {self._attempts} WHERE target=? AND feed=? AND owner IS NULL",
                                 (target, feed)).fetchone()
            row = db.execute(f"SELECT refreshed_at, payload FROM {self._snapshots} WHERE target=? AND feed=?",
                             (target, feed)).fetchone()
        snapshot = self._decode(row) if row is not None else None
        return FeedHistory(snapshot, date.fromisoformat(attempt[0]) if attempt else None, attempt[1] if attempt else None)

    def _decode(self, row) -> AdvisorySnapshot[DataT]:
        data = json.loads(zlib.decompress(row[1]))
        return AdvisorySnapshot(self._decode_payload(data), datetime.fromisoformat(row[0]))

    async def claim(self, target: str, feed: str, day: date, owner: str, now: datetime) -> FeedClaim:
        return await asyncio.to_thread(self._claim, target, feed, day, owner, now)

    def _claim(self, target: str, feed: str, day: date, owner: str, now: datetime) -> FeedClaim:
        until = now + timedelta(minutes=15)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(f"SELECT day,owner,lease_until FROM {self._attempts} WHERE target=? AND feed=?",
                                  (target, feed)).fetchone()
            if existing:
                active = datetime.fromisoformat(existing[2]) if existing[1] else None
                if active and active > now:
                    return FeedClaim(False, active)
                if existing[0] >= day.isoformat() and not active:
                    return FeedClaim(False)
            db.execute(f"INSERT OR REPLACE INTO {self._attempts}(target,feed,day,owner,lease_until) VALUES(?,?,?,?,?)",
                       (target, feed, day.isoformat(), owner, until.isoformat()))
        return FeedClaim(True)

    async def finish(self, target: str, feed: str, owner: str, snapshot: AdvisorySnapshot[DataT] | None, error: str | None) -> bool:
        return await asyncio.to_thread(self._finish, target, feed, owner, snapshot, error)

    def _finish(self, target: str, feed: str, owner: str, snapshot: AdvisorySnapshot[DataT] | None, error: str | None) -> bool:
        blob = None
        if snapshot is not None:
            payload = json.dumps(snapshot.data, default=vars, ensure_ascii=False, separators=(",", ":")).encode()
            blob = zlib.compress(payload, level=3)
        with closing(self._connect()) as db, db:
            owned = db.execute(f"UPDATE {self._attempts} SET owner=NULL,lease_until=NULL,error=? "
                               "WHERE target=? AND feed=? AND owner=?", (error, target, feed, owner)).rowcount
            if owned and snapshot is not None:
                db.execute(f"INSERT OR REPLACE INTO {self._snapshots}(target,feed,refreshed_at,payload) VALUES (?,?,?,?)",
                           (target, feed, snapshot.refreshed_at.isoformat(), blob))
            return bool(owned)

    async def abandon(self, target: str, feed: str, owner: str) -> None:
        await asyncio.to_thread(self._abandon, target, feed, owner)

    def _abandon(self, target: str, feed: str, owner: str) -> None:
        with closing(self._connect()) as db, db:
            db.execute(f"DELETE FROM {self._attempts} WHERE target=? AND feed=? AND owner=?", (target, feed, owner))
