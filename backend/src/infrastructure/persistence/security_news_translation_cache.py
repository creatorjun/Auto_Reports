# backend/src/infrastructure/persistence/security_news_translation_cache.py
import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from itertools import islice
from pathlib import Path

from src.application.ports.security_news_translation_port import NewsTranslationCachePort, TranslationFailure
from src.application.services.translation_retry_policy import (
    ATTEMPT_RESERVATION_SECONDS,
    DAILY_LIMIT_MESSAGE,
    EXHAUSTED_MESSAGE,
    translation_retry_decision,
)
from src.domain.entities.security_news_translation import (
    NewsTranslation,
    NewsTranslationInput,
    NewsTranslationReservation,
)


class SqliteNewsTranslationCache(NewsTranslationCachePort):
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._closed = False

    @contextmanager
    def _connection(self):
        if self._closed:
            raise RuntimeError("Translation cache is closed")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS translations ("
                "content_key TEXT PRIMARY KEY, title_ko TEXT NOT NULL, summary_ko TEXT NOT NULL, created_at REAL NOT NULL);"
                "CREATE TABLE IF NOT EXISTS attempts ("
                "content_key TEXT PRIMARY KEY, attempt_count INTEGER NOT NULL, next_attempt_at REAL NOT NULL);"
                "CREATE TABLE IF NOT EXISTS request_budget (day TEXT PRIMARY KEY, used INTEGER NOT NULL);"
                "CREATE TABLE IF NOT EXISTS translation_control ("
                "id INTEGER PRIMARY KEY CHECK (id=1), next_request_at REAL NOT NULL, quota_failures INTEGER NOT NULL, message TEXT);"
                "INSERT OR IGNORE INTO translation_control VALUES (1, 0, 0, NULL);"
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
            await task
            raise

    async def read(self, keys: tuple[str, ...]) -> dict[str, NewsTranslation]:
        return await self._call(self._read, keys)

    def _read(self, keys: tuple[str, ...]) -> dict[str, NewsTranslation]:
        found = {}
        with self._connection() as connection:
            for offset in range(0, len(keys), 400):
                chunk = keys[offset:offset + 400]
                query = "SELECT content_key, title_ko, summary_ko FROM translations WHERE content_key IN (" + ",".join("?" for _ in chunk) + ")"
                for key, title, summary in connection.execute(query, chunk):
                    found[key] = NewsTranslation(key, title, summary)
        return found

    async def reserve(
        self,
        inputs: tuple[NewsTranslationInput, ...],
        *,
        now: datetime,
        daily_limit: int,
        batch_size: int,
        minimum_interval_seconds: float,
        max_attempts: int,
    ) -> NewsTranslationReservation:
        return await self._call(
            self._reserve, inputs, now, daily_limit, batch_size, minimum_interval_seconds, max_attempts,
        )

    def _reserve(self, inputs, now, daily_limit, batch_size, minimum_interval_seconds, max_attempts):
        timestamp = now.timestamp()
        day = now.astimezone(timezone.utc).date().isoformat()
        with self._connection() as connection:
            next_request, _, message = connection.execute(
                "SELECT next_request_at, quota_failures, message FROM translation_control WHERE id=1",
            ).fetchone()
            if next_request > timestamp:
                return NewsTranslationReservation(
                    next_attempt_at=datetime.fromtimestamp(next_request, timezone.utc), message=message,
                )
            used = connection.execute("SELECT used FROM request_budget WHERE day=?", (day,)).fetchone()
            if daily_limit <= 0 or (used is not None and used[0] >= daily_limit):
                tomorrow = datetime.combine(now.astimezone(timezone.utc).date() + timedelta(days=1), datetime.min.time(), timezone.utc)
                return NewsTranslationReservation(
                    next_attempt_at=tomorrow,
                    message=DAILY_LIMIT_MESSAGE,
                )
            eligible = []
            retry_times = []
            seen = set()

            def unique_inputs():
                for value in inputs:
                    if value.key not in seen:
                        seen.add(value.key)
                        yield value

            candidates = unique_inputs()
            chunk_size = max(1, min(batch_size, 400))
            while chunk := tuple(islice(candidates, chunk_size)):
                keys = tuple(value.key for value in chunk)
                placeholders = ",".join("?" for _ in keys)
                translated = {row[0] for row in connection.execute(
                    f"SELECT content_key FROM translations WHERE content_key IN ({placeholders})", keys,
                )}
                pending_keys = tuple(key for key in keys if key not in translated)
                attempts = {}
                if pending_keys:
                    placeholders = ",".join("?" for _ in pending_keys)
                    attempts = {key: (count, retry) for key, count, retry in connection.execute(
                        f"SELECT content_key, attempt_count, next_attempt_at FROM attempts WHERE content_key IN ({placeholders})", pending_keys,
                    )}
                for value in chunk:
                    if value.key in translated:
                        continue
                    attempt = attempts.get(value.key)
                    if attempt is not None:
                        count, retry = attempt
                        if count >= max_attempts:
                            continue
                        if retry > timestamp:
                            retry_times.append(retry)
                            continue
                    eligible.append(value)
                    if len(eligible) >= batch_size:
                        break
                if len(eligible) >= batch_size:
                    break
                chunk_size = 400
            if not eligible:
                return NewsTranslationReservation(
                    next_attempt_at=datetime.fromtimestamp(min(retry_times), timezone.utc) if retry_times else None,
                    message=message or EXHAUSTED_MESSAGE,
                )
            connection.execute(
                "INSERT INTO request_budget (day, used) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET used=used+1",
                (day,),
            )
            connection.execute(
                "UPDATE translation_control SET next_request_at=?, message=NULL WHERE id=1",
                (timestamp + minimum_interval_seconds,),
            )
            for value in eligible:
                connection.execute(
                    "INSERT INTO attempts VALUES (?, 1, ?) ON CONFLICT(content_key) DO UPDATE "
                    "SET attempt_count=attempt_count+1, next_attempt_at=excluded.next_attempt_at",
                    (value.key, timestamp + ATTEMPT_RESERVATION_SECONDS),
                )
            return NewsTranslationReservation(tuple(eligible))

    async def complete(
        self,
        inputs: tuple[NewsTranslationInput, ...],
        translations: tuple[NewsTranslation, ...],
        *,
        now: datetime,
        failure: TranslationFailure | None = None,
    ) -> None:
        await self._call(self._complete, inputs, translations, now, failure)

    def _complete(self, inputs, translations, now, failure):
        timestamp = now.timestamp()
        valid_keys = {value.key for value in inputs}
        successes = {value.key for value in translations if value.key in valid_keys}
        with self._connection() as connection:
            for value in translations:
                if value.key not in valid_keys:
                    continue
                connection.execute(
                    "INSERT OR IGNORE INTO translations VALUES (?, ?, ?, ?)",
                    (value.key, value.title_ko, value.summary_ko, timestamp),
                )
                connection.execute("DELETE FROM attempts WHERE content_key=?", (value.key,))
            quota_failures = connection.execute(
                "SELECT quota_failures FROM translation_control WHERE id=1",
            ).fetchone()[0]
            decision = translation_retry_decision(failure, quota_failures)
            connection.execute(
                "UPDATE translation_control SET message=? WHERE id=1", (decision.message,),
            )
            if decision.quota_failures is not None:
                connection.execute(
                    "UPDATE translation_control SET quota_failures=? WHERE id=1", (decision.quota_failures,),
                )
            if decision.request_delay_seconds is not None:
                expression = "MAX(next_request_at, ?)" if decision.extend_request_delay else "?"
                connection.execute(
                    f"UPDATE translation_control SET next_request_at={expression} WHERE id=1",
                    (timestamp + decision.request_delay_seconds,),
                )
            if failure is not None:
                for value in inputs:
                    if value.key not in successes:
                        count = connection.execute(
                            "SELECT attempt_count FROM attempts WHERE content_key=?", (value.key,),
                        ).fetchone()
                        delay = decision.item_delay_seconds(count[0] if count else 1)
                        restore = "attempt_count=MAX(0, attempt_count-1), " if decision.restore_attempts else ""
                        connection.execute(
                            f"UPDATE attempts SET {restore}next_attempt_at=? WHERE content_key=?",
                            (timestamp + delay, value.key),
                        )

    async def aclose(self) -> None:
        self._closed = True
