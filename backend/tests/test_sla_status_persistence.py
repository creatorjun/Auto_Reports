# backend/tests/test_sla_status_persistence.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

from src.application.ports.sla_digest_port import SlaDigestSourcePort
from src.application.ports.sla_status_snapshot_port import SlaStatusSnapshotPort
from src.application.use_cases.sla_status import SlaStatusSourceError, SlaStatusUseCase, _snapshot
from tests.test_sla_status import entry, wait_for_refresh

NOW = datetime(2026, 10, 21, 6, tzinfo=timezone.utc)


class SlaStatusPersistenceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.source = AsyncMock(spec=SlaDigestSourcePort)
        self.source.fetch_entries.return_value = (entry(summary="새 결과"),)
        self.snapshots = AsyncMock(spec=SlaStatusSnapshotPort)
        self.snapshots.load.return_value = _snapshot((entry(summary="저장 결과"),), NOW)
        self.snapshots.save.side_effect = lambda project, snapshot: snapshot
        self.now = Mock(return_value=NOW)
        self.clock = Mock(return_value=100.0)
        self.use_case = SlaStatusUseCase(
            self.source, snapshots=self.snapshots, project_key="TACEA", now=self.now, clock=self.clock,
        )
        self.addAsyncCleanup(self.use_case.aclose)

    async def test_restart_restores_fresh_snapshot_without_contacting_jira(self):
        first, second = await asyncio.gather(self.use_case.get_snapshot(), self.use_case.get_snapshot())
        self.assertEqual("저장 결과", first.tickets[0].summary)
        self.assertEqual(first, second)
        self.assertFalse(first.refresh_in_progress)
        self.assertFalse(first.stale)
        self.source.fetch_entries.assert_not_awaited()
        self.snapshots.load.assert_awaited_once_with("TACEA")

    async def test_stale_restart_returns_saved_result_before_background_collection_finishes(self):
        self.now.return_value = NOW + timedelta(minutes=10)
        started, release = asyncio.Event(), asyncio.Event()

        async def collect():
            started.set()
            await release.wait()
            return (entry(summary="새 결과"),)

        self.source.fetch_entries.side_effect = collect
        result = await asyncio.wait_for(self.use_case.get_snapshot(), 0.2)
        self.assertEqual("저장 결과", result.tickets[0].summary)
        self.assertTrue(result.stale)
        self.assertTrue(result.refresh_in_progress)
        await started.wait()
        repeated = await self.use_case.get_snapshot(refresh=True)
        self.assertEqual(result, repeated)
        self.source.fetch_entries.assert_awaited_once_with()
        release.set()
        completed = await wait_for_refresh(self.use_case)
        self.assertEqual("새 결과", completed.tickets[0].summary)
        self.assertFalse(completed.stale)
        self.snapshots.save.assert_awaited_once()

    async def test_empty_saved_result_is_restored_without_initial_collection(self):
        self.snapshots.load.return_value = _snapshot((), NOW)
        result = await self.use_case.get_snapshot()
        self.assertEqual((0, ()), (result.ticket_count, result.tickets))
        self.source.fetch_entries.assert_not_awaited()

    async def test_first_collection_waits_for_successful_persistence_and_returns_sanitized_value(self):
        self.snapshots.load.return_value = None
        started, release = asyncio.Event(), asyncio.Event()

        async def save(project, snapshot):
            started.set()
            await release.wait()
            return replace(snapshot, tickets=(replace(snapshot.tickets[0], assignee="삭제된 사용자"),))

        self.snapshots.save.side_effect = save
        request = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        self.assertFalse(request.done())
        release.set()
        result = await request
        self.assertEqual("삭제된 사용자", result.tickets[0].assignee)
        self.assertEqual(result, await self.use_case.get_snapshot())

    async def test_persistence_failure_keeps_last_saved_data_and_manual_retry_recovers(self):
        original = await self.use_case.get_snapshot()
        self.snapshots.save.side_effect = RuntimeError("private database details")
        await self.use_case.get_snapshot(refresh=True)
        failed = await wait_for_refresh(self.use_case)
        self.assertEqual(original.tickets, failed.tickets)
        self.assertTrue(failed.stale)
        self.assertIsNotNone(failed.refresh_error)
        self.assertNotIn("private", failed.refresh_error)
        for _ in range(3):
            await self.use_case.get_snapshot()
        self.source.fetch_entries.assert_awaited_once_with()
        self.snapshots.save.side_effect = lambda project, snapshot: snapshot
        await self.use_case.get_snapshot(refresh=True)
        recovered = await wait_for_refresh(self.use_case)
        self.assertEqual("새 결과", recovered.tickets[0].summary)
        self.assertIsNone(recovered.refresh_error)

    async def test_automatic_retry_is_delayed_after_failure(self):
        self.now.return_value = NOW + timedelta(minutes=5)
        self.source.fetch_entries.side_effect = RuntimeError("unavailable")
        await self.use_case.get_snapshot()
        await wait_for_refresh(self.use_case)
        self.clock.return_value += 59
        self.assertFalse((await self.use_case.get_snapshot()).refresh_in_progress)
        self.source.fetch_entries.assert_awaited_once_with()
        self.clock.return_value += 1
        self.assertTrue((await self.use_case.get_snapshot()).refresh_in_progress)
        await wait_for_refresh(self.use_case)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_restore_failure_does_not_discard_saved_state_and_can_retry(self):
        original = self.snapshots.load.return_value
        self.snapshots.load.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(SlaStatusSourceError):
            await self.use_case.get_snapshot()
        self.source.fetch_entries.assert_not_awaited()
        self.snapshots.load.side_effect = None
        self.assertEqual(original, await self.use_case.get_snapshot())

    async def test_privacy_clear_reloads_sanitized_saved_state(self):
        await self.use_case.get_snapshot()
        old = self.snapshots.load.return_value
        self.snapshots.load.return_value = replace(old, tickets=(replace(old.tickets[0], assignee="최신 이름"),))
        await self.use_case.clear_personal_data_cache()
        restored = await self.use_case.get_snapshot()
        self.assertEqual("최신 이름", restored.tickets[0].assignee)
        self.assertEqual(2, self.snapshots.load.await_count)
        self.source.fetch_entries.assert_not_awaited()

    async def test_privacy_invalidation_cancels_detached_refresh_before_it_can_save_old_people(self):
        await self.use_case.get_snapshot()
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def ignore_cancel():
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                return (entry(assignee="옛 이름"),)

        self.source.fetch_entries.side_effect = ignore_cancel
        await self.use_case.get_snapshot(refresh=True)
        await started.wait()
        await self.use_case.clear_personal_data_cache()
        self.assertTrue(cancelled.is_set())
        self.snapshots.save.assert_not_awaited()
        restored = await self.use_case.get_snapshot()
        self.assertEqual("담당자", restored.tickets[0].assignee)

    async def test_background_refresh_survives_the_request_and_shutdown_cancels_it(self):
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def collect():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.source.fetch_entries.side_effect = collect
        request = asyncio.create_task(self.use_case.get_snapshot(refresh=True))
        self.assertTrue((await request).refresh_in_progress)
        await started.wait()
        self.assertFalse(cancelled.is_set())
        await self.use_case.aclose()
        self.assertTrue(cancelled.is_set())
        self.snapshots.save.assert_not_awaited()
