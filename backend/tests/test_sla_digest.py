# backend/tests/test_sla_digest.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from src.application.ports.email_port import EmailPort
from src.application.ports.sla_digest_port import SlaDigestRendererPort, SlaDigestSourcePort
from src.application.use_cases.notify_sla_digest import NotifySlaDigestUseCase
from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestEntry


NOW = datetime(2026, 10, 20, 9, tzinfo=KST)
ENTRY = SlaDigestEntry(
    key="TAC-1", summary="원격 지원", status="처리 중", assignee="담당자",
    sla_id="12", sla_name="처리 중", goal_millis=10000, remaining_millis=3000,
)


class SlaDigestTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.source = AsyncMock(spec=SlaDigestSourcePort)
        self.source.fetch_entries.return_value = (ENTRY,)
        self.email = AsyncMock(spec=EmailPort)
        self.renderer = Mock(spec=SlaDigestRendererPort)
        self.renderer.render.return_value = "SLA digest body"
        self.use_case = NotifySlaDigestUseCase(
            self.source, self.email, self.renderer,
            ["test@example.test"], "https://jira.example.test",
        )

    async def test_inclusive_remaining_threshold_and_paused_excludes_breaches(self) -> None:
        selected = (
            ENTRY,
            replace(ENTRY, key="TAC-2", remaining_millis=0),
            replace(ENTRY, key="TAC-4", remaining_millis=2000, paused=True),
        )
        self.source.fetch_entries.return_value = (
            *selected,
            replace(ENTRY, key="BREACHED", remaining_millis=-2000, breached=True),
            replace(ENTRY, key="BREACHED-ZERO", remaining_millis=0, breached=True),
            replace(ENTRY, key="BREACHED-POSITIVE", remaining_millis=2000, breached=True),
            replace(ENTRY, key="NEGATIVE-REMAINING", remaining_millis=-1, breached=False),
            replace(ENTRY, key="ABOVE-THRESHOLD", remaining_millis=3001),
            replace(ENTRY, key="NO-GOAL", goal_millis=0, remaining_millis=-1),
            replace(ENTRY, key="NEGATIVE-GOAL", goal_millis=-1, remaining_millis=-1),
        )

        self.assertEqual(3, await self.use_case.execute(NOW))

        self.renderer.render.assert_called_once_with(selected, "https://jira.example.test", NOW)
        self.email.send.assert_awaited_once_with(
            to=["test@example.test"], subject="[TAC] SLA 일일 알림 2026-10-20 — 3건", body="SLA digest body",
        )

    async def test_one_message_for_all_stages_counts_distinct_tickets(self) -> None:
        entries = (ENTRY, replace(ENTRY, sla_id="13", sla_name="결과 대기 중"))
        self.source.fetch_entries.return_value = entries

        self.assertEqual(1, await self.use_case.execute(NOW))

        self.renderer.render.assert_called_once_with(entries, "https://jira.example.test", NOW)
        self.email.send.assert_awaited_once()
        self.assertEqual("[TAC] SLA 일일 알림 2026-10-20 — 1건", self.email.send.await_args.kwargs["subject"])

    async def test_any_breached_stage_excludes_the_entire_ticket(self) -> None:
        for breach in (
            replace(ENTRY, sla_id="13", remaining_millis=0, breached=True),
            replace(ENTRY, sla_id="13", remaining_millis=-1, breached=False),
        ):
            with self.subTest(breach=breach):
                self.source.fetch_entries.return_value = (ENTRY, breach)

                self.assertEqual(0, await self.use_case.execute(NOW))

        self.renderer.render.assert_not_called()
        self.email.send.assert_not_awaited()

    async def test_past_completed_breach_marker_excludes_the_entire_ticket(self) -> None:
        eligible = replace(ENTRY, key="TAC-2")
        self.source.fetch_entries.return_value = (
            ENTRY,
            replace(ENTRY, sla_id="13", issue_has_breached_sla=True, remaining_millis=9000),
            eligible,
        )

        self.assertEqual(1, await self.use_case.execute(NOW))

        self.renderer.render.assert_called_once_with((eligible,), "https://jira.example.test", NOW)

    async def test_empty_selection_does_not_send(self) -> None:
        self.source.fetch_entries.return_value = (replace(ENTRY, remaining_millis=3001),)

        self.assertEqual(0, await self.use_case.execute(NOW))

        self.renderer.render.assert_not_called()
        self.email.send.assert_not_awaited()

    async def test_empty_recipients_do_not_fetch_or_send(self) -> None:
        use_case = NotifySlaDigestUseCase(self.source, self.email, self.renderer, ["  "], "https://jira.example.test")

        self.assertEqual(0, await use_case.execute(NOW))

        self.source.fetch_entries.assert_not_awaited()
        self.email.send.assert_not_awaited()

    async def test_one_delivery_per_kst_day_and_repeat_on_next_day(self) -> None:
        self.assertEqual(1, await self.use_case.execute(NOW))
        self.assertEqual(0, await self.use_case.execute(NOW + timedelta(hours=1)))
        self.assertEqual(1, await self.use_case.execute(NOW + timedelta(days=1)))

        self.assertEqual(2, self.email.send.await_count)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_concurrent_execution_sends_only_one_email(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def deliver(**kwargs: object) -> None:
            started.set()
            await release.wait()

        self.email.send.side_effect = deliver
        first = asyncio.create_task(self.use_case.execute(NOW))
        await started.wait()
        second = asyncio.create_task(self.use_case.execute(NOW))
        release.set()

        self.assertEqual([1, 0], await asyncio.gather(first, second))
        self.email.send.assert_awaited_once()
        self.source.fetch_entries.assert_awaited_once()

    async def test_adapter_failures_propagate_and_allow_same_day_retry(self) -> None:
        for operation in (self.source.fetch_entries, self.renderer.render, self.email.send):
            with self.subTest(operation=operation):
                use_case = NotifySlaDigestUseCase(
                    self.source, self.email, self.renderer,
                    ["test@example.test"], "https://jira.example.test",
                )
                operation.side_effect = RuntimeError("adapter failed")

                with self.assertRaisesRegex(RuntimeError, "adapter failed"):
                    await use_case.execute(NOW)

                operation.side_effect = None
                self.assertEqual(1, await use_case.execute(NOW))
                self.assertEqual(0, await use_case.execute(NOW))

    async def test_cancellation_does_not_mark_delivery_complete(self) -> None:
        self.email.send.side_effect = asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await self.use_case.execute(NOW)

        self.email.send.side_effect = None
        self.assertEqual(1, await self.use_case.execute(NOW))

    async def test_timezone_normalization_uses_kst_date(self) -> None:
        utc_now = datetime(2026, 10, 19, 16, tzinfo=timezone.utc)

        self.assertEqual(1, await self.use_case.execute(utc_now))
        self.assertEqual(0, await self.use_case.execute(NOW))

        self.assertEqual(datetime(2026, 10, 20, 1, tzinfo=KST), self.renderer.render.call_args.args[2])
        self.assertIn("2026-10-20", self.email.send.await_args.kwargs["subject"])

    async def test_default_clock_is_kst(self) -> None:
        with patch("src.application.use_cases.notify_sla_digest.datetime") as clock:
            clock.now.return_value = NOW
            self.assertEqual(1, await self.use_case.execute())

        clock.now.assert_called_once_with(KST)
        self.renderer.render.assert_called_once_with((ENTRY,), "https://jira.example.test", NOW)

    async def test_dry_run_counts_without_rendering_sending_or_marking_day_complete(self) -> None:
        self.source.fetch_entries.return_value = (ENTRY, replace(ENTRY, sla_id="13"))

        result = await self.use_case.trigger(dry_run=True, now=NOW)

        self.assertEqual(("preview", 1, 2, 1, NOW), (
            result.status, result.ticket_count, result.sla_count, result.recipient_count, result.generated_at,
        ))
        self.renderer.render.assert_not_called()
        self.email.send.assert_not_awaited()
        self.assertEqual(1, await self.use_case.execute(NOW))

    async def test_preview_after_delivery_still_reads_live_jira_without_resetting_duplicate_guard(self) -> None:
        self.assertEqual(1, await self.use_case.execute(NOW))
        self.source.fetch_entries.return_value = ()

        preview = await self.use_case.trigger(dry_run=True, now=NOW)
        repeated = await self.use_case.trigger(now=NOW)

        self.assertEqual(("preview", 0, 0), (preview.status, preview.ticket_count, preview.sla_count))
        self.assertEqual(("already_sent", 1, 1), (repeated.status, repeated.ticket_count, repeated.sla_count))
        self.assertEqual(2, self.source.fetch_entries.await_count)
        self.email.send.assert_awaited_once()

    async def test_trigger_reports_no_matches_without_sending(self) -> None:
        self.source.fetch_entries.return_value = ()

        result = await self.use_case.trigger(now=NOW)

        self.assertEqual(("no_matches", 0, 0, 1), (
            result.status, result.ticket_count, result.sla_count, result.recipient_count,
        ))
        self.email.send.assert_not_awaited()

    async def test_trigger_and_scheduled_execution_share_one_delivery_lock(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def deliver(**kwargs: object) -> None:
            started.set()
            await release.wait()

        self.email.send.side_effect = deliver
        scheduled = asyncio.create_task(self.use_case.execute(NOW))
        await started.wait()
        manual = asyncio.create_task(self.use_case.trigger(now=NOW))
        release.set()

        scheduled_count, manual_result = await asyncio.gather(scheduled, manual)

        self.assertEqual(1, scheduled_count)
        self.assertEqual("already_sent", manual_result.status)
        self.email.send.assert_awaited_once()

    async def test_failed_preview_propagates_and_does_not_prevent_actual_delivery(self) -> None:
        self.source.fetch_entries.side_effect = RuntimeError("Jira unavailable")

        with self.assertRaisesRegex(RuntimeError, "Jira unavailable"):
            await self.use_case.trigger(dry_run=True, now=NOW)

        self.source.fetch_entries.side_effect = None
        result = await self.use_case.trigger(now=NOW)
        self.assertEqual("sent", result.status)
