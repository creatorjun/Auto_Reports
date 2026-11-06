import asyncio
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.application.ports.sla_digest_port import SlaDigestSourcePort
from src.application.ports.sla_status_port import SlaStatusDetailsPort
from src.application.ports.sla_status_snapshot_port import SlaStatusSnapshotPort
from src.application.use_cases.sla_status import SlaStatusUseCase, _snapshot, _with_details
from tests.test_sla_status import detailed_issue, entry, wait_for_refresh


class SlaStatusConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        now = datetime(2026, 10, 21, 6, tzinfo=timezone.utc)
        self.source = AsyncMock(spec=SlaDigestSourcePort)
        self.source.fetch_entries.return_value = (entry(),)
        self.details = AsyncMock(spec=SlaStatusDetailsPort)
        self.details.fetch_details.return_value = (detailed_issue(),)
        self.snapshots = AsyncMock(spec=SlaStatusSnapshotPort)
        self.snapshots.load.return_value = _snapshot((entry(summary="저장 결과"),), now)
        self.snapshots.save.side_effect = lambda project, snapshot: snapshot
        self.use_case = SlaStatusUseCase(
            self.source, self.details, snapshots=self.snapshots, now=lambda: now,
        )
        self.addAsyncCleanup(self.use_case.aclose)

    async def test_cache_invalidation_during_restore_reloads_saved_list_before_collecting(self):
        old = self.snapshots.load.return_value
        updated = replace(old, tickets=(replace(old.tickets[0], assignee="최신 이름"),))
        started, release = asyncio.Event(), asyncio.Event()
        loads = 0

        async def load(project):
            nonlocal loads
            loads += 1
            if loads == 1:
                started.set()
                await release.wait()
                return old
            return updated

        async def collect():
            await asyncio.Event().wait()

        self.snapshots.load.side_effect = load
        self.source.fetch_entries.side_effect = collect
        request = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        await self.use_case.clear_personal_data_cache()
        release.set()
        result = await asyncio.wait_for(request, 0.5)
        self.assertEqual("최신 이름", result.tickets[0].assignee)
        self.assertEqual(2, loads)
        self.source.fetch_entries.assert_not_awaited()

    async def test_page_entry_returns_saved_list_while_status_durations_are_calculated(self):
        saved = await self.use_case.get_snapshot()
        started, release, finished = threading.Event(), threading.Event(), threading.Event()

        def calculate(*args):
            started.set()
            release.wait(1)
            try:
                return _with_details(*args)
            finally:
                finished.set()

        with patch("src.application.use_cases.sla_status._with_details", side_effect=calculate):
            await self.use_case.get_snapshot(refresh=True)
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                result = await asyncio.wait_for(self.use_case.get_snapshot(), 0.5)
                self.assertFalse(finished.is_set(), "Page entry waited for background calculation")
                self.assertEqual(saved.tickets, result.tickets)
                self.assertTrue(result.refresh_in_progress)
            finally:
                release.set()
                await wait_for_refresh(self.use_case)

    async def test_invalidated_calculation_cannot_replace_sanitized_saved_list(self):
        saved = await self.use_case.get_snapshot()
        sanitized = replace(saved, tickets=(replace(saved.tickets[0], assignee="최신 이름"),))
        started, release, finished = threading.Event(), threading.Event(), threading.Event()

        def calculate(*args):
            started.set()
            release.wait(2)
            try:
                return _with_details(*args)
            finally:
                finished.set()

        with patch("src.application.use_cases.sla_status._with_details", side_effect=calculate):
            await self.use_case.get_snapshot(refresh=True)
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                self.snapshots.load.return_value = sanitized
                await self.use_case.clear_personal_data_cache()
                restored = await self.use_case.get_snapshot()
                self.assertEqual(sanitized.tickets, restored.tickets)
            finally:
                release.set()
                self.assertTrue(await asyncio.to_thread(finished.wait, 2))
        self.snapshots.save.assert_not_awaited()
        self.assertEqual(sanitized.tickets, (await self.use_case.get_snapshot()).tickets)

    async def test_calculation_deadline_preserves_saved_list_and_discards_late_result(self):
        saved = await self.use_case.get_snapshot()
        self.use_case._timeout_seconds = 0.1
        started, release, finished = threading.Event(), threading.Event(), threading.Event()

        def calculate(*args):
            started.set()
            release.wait(2)
            try:
                return _with_details(*args)
            finally:
                finished.set()

        with patch("src.application.use_cases.sla_status._with_details", side_effect=calculate):
            await self.use_case.get_snapshot(refresh=True)
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                result = await wait_for_refresh(self.use_case)
                self.assertEqual(saved.tickets, result.tickets)
                self.assertIsNotNone(result.refresh_error)
                self.assertFalse(finished.is_set())
            finally:
                release.set()
                self.assertTrue(await asyncio.to_thread(finished.wait, 2))
        self.snapshots.save.assert_not_awaited()
        self.assertEqual(saved.tickets, (await self.use_case.get_snapshot()).tickets)
