# backend/tests/test_persistence_performance.py
import asyncio
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.domain.entities.security_news_translation import NewsTranslationInput
from src.infrastructure.persistence.security_news_translation_cache import SqliteNewsTranslationCache


class TracedTranslationCache(SqliteNewsTranslationCache):
    def __init__(self, path):
        super().__init__(path)
        self.statements = []

    @contextmanager
    def _connection(self):
        with super()._connection() as connection:
            connection.set_trace_callback(self.statements.append)
            yield connection


class TranslationReservationPerformanceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "translations.sqlite3")
        self.cache = TracedTranslationCache(self.path)
        self.now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.options = dict(now=self.now, daily_limit=10, batch_size=3, minimum_interval_seconds=0, max_attempts=3)

    async def asyncTearDown(self):
        await self.cache.aclose()
        self.directory.cleanup()

    async def test_pending_candidates_use_bounded_queries_without_consuming_budget(self):
        inputs = tuple(NewsTranslationInput(f"key-{index}", f"title-{index}", "") for index in range(1001))
        retry = self.now + timedelta(hours=1)
        with self.cache._connection() as connection:
            connection.executemany("INSERT INTO attempts VALUES (?, 1, ?)", ((value.key, retry.timestamp()) for value in inputs))
        self.cache.statements.clear()
        result = await self.cache.reserve(inputs, **self.options)
        self.assertEqual((), result.inputs)
        self.assertEqual(retry, result.next_attempt_at)
        queries = [statement for statement in self.cache.statements if statement.startswith("SELECT") and ("FROM translations" in statement or "FROM attempts" in statement)]
        self.assertEqual(8, len(queries))
        with self.cache._connection() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM request_budget").fetchone()[0])
            self.assertEqual(1001, connection.execute("SELECT COUNT(*) FROM attempts WHERE attempt_count=1").fetchone()[0])

    async def test_ready_batch_stops_reading_candidates_immediately(self):
        visited = []

        class BoundedInputs(tuple):
            def __iter__(self):
                for value in super().__iter__():
                    visited.append(value.key)
                    if len(visited) > 10:
                        raise AssertionError("Read beyond the ready batch")
                    yield value

        inputs = BoundedInputs(NewsTranslationInput(f"key-{index}", f"title-{index}", "") for index in range(1001))
        result = await self.cache.reserve(inputs, **{**self.options, "batch_size": 10})
        self.assertEqual(inputs[:10], result.inputs)
        self.assertEqual(10, len(visited))
        queries = [statement for statement in self.cache.statements if statement.startswith("SELECT") and ("FROM translations" in statement or "FROM attempts" in statement)]
        self.assertEqual(2, len(queries))

    async def test_translated_candidates_never_read_attempts_or_consume_budget(self):
        inputs = tuple(NewsTranslationInput(f"key-{index}", f"title-{index}", "") for index in range(1001))
        with self.cache._connection() as connection:
            connection.executemany("INSERT INTO translations VALUES (?, 'translated', '', 0)", ((value.key,) for value in inputs))
        self.cache.statements.clear()
        result = await self.cache.reserve(inputs, **self.options)
        self.assertEqual((), result.inputs)
        self.assertIsNone(result.next_attempt_at)
        queries = [statement for statement in self.cache.statements if statement.startswith("SELECT") and "FROM attempts" in statement]
        self.assertEqual([], queries)
        with self.cache._connection() as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM request_budget").fetchone()[0])

    async def test_chunk_boundaries_preserve_first_duplicate_order_and_retry_rules(self):
        inputs = tuple(NewsTranslationInput(f"key-{index}", f"title-{index}", "") for index in range(405))
        with self.cache._connection() as connection:
            connection.executemany("INSERT INTO translations VALUES (?, 'translated', '', 0)", ((value.key,) for value in inputs[:399]))
            connection.executemany("INSERT INTO attempts VALUES (?, ?, ?)", (
                ("key-399", 1, self.now.timestamp() + 60),
                ("key-400", 3, 0),
                ("key-402", 1, self.now.timestamp()),
            ))
        reordered = inputs[:402] + (NewsTranslationInput("key-401", "ignored duplicate", ""),) + inputs[402:]
        result = await self.cache.reserve(reordered, **self.options)
        self.assertEqual(inputs[401:404], result.inputs)
        with self.cache._connection() as connection:
            attempts = dict(connection.execute("SELECT content_key, attempt_count FROM attempts"))
            self.assertEqual({"key-399": 1, "key-400": 3, "key-401": 1, "key-402": 2, "key-403": 1}, attempts)
            self.assertEqual(1, connection.execute("SELECT SUM(used) FROM request_budget").fetchone()[0])
            self.assertIsNone(connection.execute("SELECT 1 FROM attempts WHERE content_key='key-404'").fetchone())

    async def test_simultaneous_workers_reserve_disjoint_batches_with_one_transaction_each(self):
        inputs = tuple(NewsTranslationInput(f"key-{index}", f"title-{index}", "") for index in range(6))
        with self.cache._connection():
            pass
        second = SqliteNewsTranslationCache(self.path)
        try:
            results = await asyncio.gather(self.cache.reserve(inputs, **self.options), second.reserve(inputs, **self.options))
        finally:
            await second.aclose()
        keys = [value.key for result in results for value in result.inputs]
        self.assertEqual(6, len(keys))
        self.assertEqual(6, len(set(keys)))
        with self.cache._connection() as connection:
            self.assertEqual(2, connection.execute("SELECT SUM(used) FROM request_budget").fetchone()[0])
            self.assertEqual(6, connection.execute("SELECT COUNT(*) FROM attempts WHERE attempt_count=1").fetchone()[0])
