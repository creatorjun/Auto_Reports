# backend/src/infrastructure/persistence/security_news_translation_cache.py
import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.ports.security_news_translation_port import NewsTranslationCachePort, TranslationFailure
from src.domain.entities.security_news_translation import (
    NewsTranslation,
    NewsTranslationInput,
    NewsTranslationReservation,
)


FAILURE_MESSAGES = {
    "quota": "Gemini API 요청 한도에 도달하여 번역을 일시 중지했습니다. 저장된 번역과 원문을 표시합니다.",
    "billing": "Gemini API 크레딧이 부족하여 번역을 일시 중지했습니다. 저장된 번역과 원문을 표시합니다.",
    "authorization": "Gemini API 설정·인증 또는 모델 접근 권한을 확인해야 합니다. 저장된 번역과 원문을 표시합니다.",
    "provider": "번역 서비스 응답이 지연되어 일부 항목의 번역을 나중에 다시 시도합니다.",
    "invalid": "일부 번역 결과를 검증하지 못해 원문을 표시합니다. 잠시 후 다시 시도합니다.",
}


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
                    message="오늘의 번역 요청 한도에 도달했습니다. 저장된 번역과 원문을 표시하며 다음 UTC 날짜에 재개합니다.",
                )
            eligible = []
            retry_times = []
            seen = set()
            for value in inputs:
                if value.key in seen:
                    continue
                seen.add(value.key)
                if connection.execute("SELECT 1 FROM translations WHERE content_key=?", (value.key,)).fetchone():
                    continue
                attempt = connection.execute(
                    "SELECT attempt_count, next_attempt_at FROM attempts WHERE content_key=?", (value.key,),
                ).fetchone()
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
            if not eligible:
                return NewsTranslationReservation(
                    next_attempt_at=datetime.fromtimestamp(min(retry_times), timezone.utc) if retry_times else None,
                    message=message or "일부 항목은 번역 자동 재시도가 제한되어 원문을 표시합니다.",
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
                    (value.key, timestamp + 300),
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
            if failure in {"quota", "billing", "authorization"}:
                quota_failures = connection.execute(
                    "SELECT quota_failures FROM translation_control WHERE id=1",
                ).fetchone()[0] + 1
                delay = min(86400, 3600 * (2 ** min(quota_failures - 1, 5))) if failure == "quota" else 86400
                connection.execute(
                    "UPDATE translation_control SET next_request_at=?, quota_failures=?, message=? WHERE id=1",
                    (timestamp + delay, quota_failures, FAILURE_MESSAGES[failure]),
                )
                for value in inputs:
                    if value.key not in successes:
                        connection.execute(
                            "UPDATE attempts SET attempt_count=MAX(0, attempt_count-1), next_attempt_at=? WHERE content_key=?",
                            (timestamp + delay, value.key),
                        )
            elif failure is not None:
                connection.execute(
                    "UPDATE translation_control SET message=? WHERE id=1", (FAILURE_MESSAGES[failure],),
                )
                if failure == "provider":
                    connection.execute(
                        "UPDATE translation_control SET next_request_at=MAX(next_request_at, ?) WHERE id=1",
                        (timestamp + 300,),
                    )
                for value in inputs:
                    if value.key not in successes:
                        count = connection.execute(
                            "SELECT attempt_count FROM attempts WHERE content_key=?", (value.key,),
                        ).fetchone()
                        delay = min(86400, 300 * (2 ** min((count[0] if count else 1) - 1, 8)))
                        connection.execute(
                            "UPDATE attempts SET next_attempt_at=? WHERE content_key=?", (timestamp + delay, value.key),
                        )
            else:
                connection.execute(
                    "UPDATE translation_control SET quota_failures=0, message=NULL WHERE id=1",
                )

    async def aclose(self) -> None:
        self._closed = True
