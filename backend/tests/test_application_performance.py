# backend/tests/test_application_performance.py
import asyncio
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.application.ports.jira_port import JiraIssue
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.security_news_translation import SecurityNewsTranslationService, translation_key
from src.application.use_cases.security_news import SecurityNewsUseCase
from src.application.widgets.resolution_collector import ResolutionCollector
from src.domain.entities.security_news import SecurityNewsItem, SecurityNewsSource, SecurityNewsSourceResult
from src.domain.entities.security_news_translation import NewsTranslation


class SecurityNewsPerformanceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.item = SecurityNewsItem(
            "first", "nvd", "cve", "Security issue in product 1.2", "A vulnerability affects product 1.2.",
            "https://example.com/", published_at=self.now, cve_ids=("CVE-2026-1234",),
        )
        self.source = AsyncMock()
        self.source.sources = (
            SecurityNewsSource("nvd", "NVD", "https://example.com/", "cve"),
            SecurityNewsSource("kev", "KEV", "https://example.com/", "cve"),
        )
        self.results = {
            "nvd": SecurityNewsSourceResult((self.item,)),
            "kev": SecurityNewsSourceResult((), frozenset({"CVE-2026-1234"})),
        }
        self.source.fetch.side_effect = lambda source_id: self.results[source_id]
        self.translation = SecurityNewsTranslationService(AsyncMock(), AsyncMock())
        self.service = SecurityNewsUseCase(self.source, clock=lambda: self.now)

    async def asyncTearDown(self):
        await self.service.aclose()
        await self.translation.aclose()

    async def refresh(self):
        self.now += timedelta(minutes=1)
        await self.service.get_snapshot(refresh=True)
        await self.service._task
        return await self.service.get_snapshot()

    async def test_repeated_reads_reuse_immutable_items_but_refresh_metadata(self):
        first = await self.refresh()
        self.now += timedelta(seconds=15)
        second = await self.service.get_snapshot()
        self.assertIs(first.items, second.items)
        self.assertEqual(60, first.retry_after_seconds)
        self.assertEqual(45, second.retry_after_seconds)
        self.assertTrue(second.items[0].known_exploited)
        self.assertFalse(self.item.known_exploited)
        with self.assertRaises(FrozenInstanceError):
            second.items[0].title = "changed"
        self.assertEqual(2, self.source.fetch.await_count)

    async def test_successful_refresh_invalidates_exploitation_sorting_and_removed_items(self):
        first = await self.refresh()
        older = replace(self.item, id="older", published_at=self.now - timedelta(days=1))
        changed = replace(self.item, title="Updated security issue", published_at=self.now)
        self.results["nvd"] = SecurityNewsSourceResult((older, changed, changed))
        self.results["kev"] = SecurityNewsSourceResult(())
        second = await self.refresh()
        self.assertEqual(["first", "older"], [item.id for item in second.items])
        self.assertEqual(changed.title, second.items[0].title)
        self.assertFalse(second.items[0].known_exploited)
        self.assertTrue(first.items[0].known_exploited)
        self.results["nvd"] = SecurityNewsSourceResult(())
        self.assertEqual((), (await self.refresh()).items)

    async def test_failed_refresh_keeps_items_but_marks_sources_stale(self):
        first = await self.refresh()
        self.source.fetch.side_effect = TimeoutError()
        with self.assertLogs("src.application.use_cases.security_news", level="WARNING"):
            second = await self.refresh()
        self.assertIs(first.items, second.items)
        self.assertEqual({"stale"}, {source.status for source in second.sources})
        self.assertEqual({"ok"}, {source.status for source in first.sources})

    async def test_translation_completion_and_replacement_are_visible_without_source_refresh(self):
        advisory = replace(self.item, id="advisory", source_id="cisco", kind="advisory")
        self.source.sources += (SecurityNewsSource("cisco", "Cisco", "https://example.com/", "advisory"),)
        self.results["cisco"] = SecurityNewsSourceResult((advisory,))
        await self.service.aclose()
        self.service = SecurityNewsUseCase(self.source, clock=lambda: self.now)
        first = await self.refresh()
        self.service._translation = self.translation
        pending = await self.service.get_snapshot()
        self.assertEqual(1, pending.translation.pending_count)
        key = translation_key(advisory.title, advisory.summary)
        self.translation._translations[key] = NewsTranslation(key, "", "번역 내용")
        self.translation._message = "현재 번역 상태"
        translated = await self.service.get_snapshot()
        items = {item.id: item for item in translated.items}
        self.assertEqual("번역 내용", items["advisory"].summary_ko)
        self.assertIsNone(items["advisory"].title_ko)
        self.assertIsNone(items["first"].title_ko)
        self.assertIsNone(items["first"].summary_ko)
        self.assertEqual(1, translated.translation.translated_count)
        self.assertEqual(0, translated.translation.pending_count)
        self.assertEqual("현재 번역 상태", translated.translation.message)
        self.assertTrue(all(item.title_ko is None and item.summary_ko is None for item in first.items))
        self.assertEqual(advisory.title, items["advisory"].title)
        self.translation._translations[key] = NewsTranslation(key, "", "수정된 내용")
        updated = {item.id: item for item in (await self.service.get_snapshot()).items}
        self.assertEqual("수정된 내용", updated["advisory"].summary_ko)
        self.assertIsNone(updated["advisory"].title_ko)
        self.assertIsNone(updated["first"].summary_ko)
        self.assertEqual(3, self.source.fetch.await_count)
        self.assertIsNone(self.translation._task)

    async def test_translation_preparation_is_reused_only_for_unchanged_active_content(self):
        with patch("src.application.services.security_news_translation.translation_key", wraps=translation_key) as hashing:
            self.translation.snapshot((self.item, self.item), start=False)
            self.assertEqual(1, hashing.call_count)
            self.translation.snapshot((replace(self.item, known_exploited=True),), start=False)
            self.assertEqual(1, hashing.call_count)
            changed = replace(self.item, summary="New summary 1.3")
            self.translation.snapshot((changed,), start=False)
            self.assertEqual(2, hashing.call_count)
            self.assertEqual(1, len(self.translation._prepared))
            self.translation.snapshot((), start=False)
            self.assertEqual({}, self.translation._prepared)
            self.translation.snapshot((self.item,), start=False)
            self.assertEqual(3, hashing.call_count)

    async def test_translation_preparation_preserves_source_language_rules(self):
        advisory = replace(self.item, source_id="cisco", kind="advisory")
        self.assertEqual(1, self.translation.snapshot((advisory,), start=False)[1].pending_count)
        korean_source = replace(advisory, source_id="kisa")
        self.assertEqual(0, self.translation.snapshot((korean_source,), start=False)[1].pending_count)
        self.assertEqual(1, self.translation.snapshot((korean_source, advisory, self.item), start=False)[1].pending_count)
        self.assertEqual(0, self.translation.snapshot((self.item,), start=False)[1].pending_count)
        korean = replace(advisory, title="보안 취약점 정보를 안내합니다", summary="취약점의 상세한 내용과 대응 방안을 확인하세요")
        self.assertEqual(0, self.translation.snapshot((korean,), start=False)[1].pending_count)


class ResolutionWorkerPerformanceTest(unittest.IsolatedAsyncioTestCase):
    def collector(self, jira):
        queries = WidgetQueryBuilder(QueryConfig("T", [], [], [], 30, 2026, "cf[1]", "cf[2]")).build(datetime(2026, 1, 3))
        return ResolutionCollector(jira, queries, queries.week_end)

    def jira(self, count=20):
        jira = AsyncMock()
        jira.get_issues.return_value = [JiraIssue(
            key=f"T-{index}", status="Closed", created="2026-01-01", resolved="2026-01-03",
        ) for index in range(count)]
        return jira

    async def test_slow_first_request_does_not_block_later_work_and_order_is_preserved(self):
        jira = self.jira()
        blocked, progressed, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        active = 0
        maximum = 0

        async def fetch(key):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            try:
                if key == "T-0":
                    blocked.set()
                    await release.wait()
                else:
                    await asyncio.sleep(0)
                if key == "T-19":
                    progressed.set()
                return []
            finally:
                active -= 1

        jira.get_issue_status_changes.side_effect = fetch
        task = asyncio.create_task(self.collector(jira).collect())
        try:
            await asyncio.wait_for(blocked.wait(), 1)
            await asyncio.wait_for(progressed.wait(), 1)
            self.assertFalse(task.done())
            self.assertLessEqual(maximum, 5)
            release.set()
            result = await task
            self.assertEqual([f"T-{index}" for index in range(20)], [issue.key for issue in result.data.stage_issues])
            self.assertEqual(20, result.total)
            self.assertTrue(all(issue.by_stage_hours == {"Closed": 48} for issue in result.data.stage_issues))
            self.assertEqual(0, active)
        finally:
            release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_cancellation_reclaims_all_workers_without_starting_queued_work(self):
        jira = self.jira()
        ready = asyncio.Event()
        started = []
        finished = []

        async def fetch(key):
            started.append(key)
            if len(started) == 5:
                ready.set()
            try:
                await asyncio.Event().wait()
            finally:
                finished.append(key)

        jira.get_issue_status_changes.side_effect = fetch
        task = asyncio.create_task(self.collector(jira).collect())
        await asyncio.wait_for(ready.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(5, len(started))
        self.assertCountEqual(started, finished)

    async def test_immediate_cache_hits_yield_to_cancellation_before_processing_the_full_list(self):
        jira = self.jira(100)
        ready = asyncio.Event()
        started = []

        async def fetch(key):
            started.append(key)
            if len(started) == 5:
                ready.set()
            return []

        jira.get_issue_status_changes.side_effect = fetch
        task = asyncio.create_task(self.collector(jira).collect())
        await asyncio.wait_for(ready.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertLess(len(started), 100)

    async def test_provider_failure_is_preserved_and_reclaims_every_worker(self):
        jira = self.jira()
        ready = asyncio.Event()
        started = []
        finished = []
        failure = RuntimeError("history unavailable")

        async def fetch(key):
            started.append(key)
            if len(started) == 5:
                ready.set()
            try:
                if key == "T-0":
                    await ready.wait()
                    raise failure
                await asyncio.Event().wait()
            finally:
                finished.append(key)

        jira.get_issue_status_changes.side_effect = fetch
        with self.assertRaises(RuntimeError) as caught:
            await self.collector(jira).collect()
        self.assertIs(failure, caught.exception)
        self.assertEqual(5, len(started))
        self.assertCountEqual(started, finished)
