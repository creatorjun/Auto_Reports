# backend/tests/test_sla_status.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import httpx

from src.application.ports.sla_digest_port import SlaDigestSourcePort
from src.application.ports.sla_status_port import SlaStatusDetailsPort
from src.application.use_cases.sla_status import SlaStatusSourceError, SlaStatusUseCase
from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestEntry
from src.domain.entities.sla_clock import SlaClockCalendar, SlaClockWorkingTime
from src.domain.entities.sla_violation_report import SlaViolationChange, SlaViolationCycle, SlaViolationIssue
from src.infrastructure.external.sla_digest_jira_source import SlaDigestJiraSource
from src.presentation.schemas.sla_status_schema import SlaStatusSnapshotSchema


def entry(key: str = "TACEA-1", **overrides) -> SlaDigestEntry:
    return replace(SlaDigestEntry(
        key=key, summary="점검 요청", status="자료 요청 중", assignee="담당자",
        sla_id="customfield_10001", sla_name="최초 응답", goal_millis=100_000,
        remaining_millis=20_000,
    ), **overrides)


def detailed_issue(key: str = "TACEA-1", **overrides) -> SlaViolationIssue:
    created = datetime(2026, 10, 21, 9, tzinfo=KST)
    changed = datetime(2026, 10, 21, 10, tzinfo=KST)
    collected = datetime(2026, 10, 21, 11, tzinfo=KST)
    return replace(SlaViolationIssue(
        key=key, summary="최신 점검 요청", created_at=created, current_status="검토 중",
        customer="고객사", partners=("파트너사",), reporter="보고자", assignee="새 담당자",
        tac_assignee="TAC 담당자", issue_type="인시던트",
        cycles=(SlaViolationCycle(
            "resolution", None, breached=False, ongoing=True, paused=False,
            goal_ms=9_000_000, elapsed_ms=7_200_000, started_at=created,
        ),),
        changes=(SlaViolationChange(changed, "할 일", "검토 중"),),
        clock_calendars=(SlaClockCalendar("1", "평일 9~18", "Asia/Seoul", tuple(
            SlaClockWorkingTime(day, 9 * 3_600_000, 18 * 3_600_000) for day in range(5)
        )),),
        clock_snapshot_before=collected, clock_snapshot_after=collected,
        reporter_account_id="private-reporter-id", assignee_account_id="private-assignee-id",
        tac_assignee_account_id="private-tac-id", personal_data_retrieved_at=collected.isoformat(),
    ), **overrides)


async def wait_for_refresh(use_case: SlaStatusUseCase):
    async with asyncio.timeout(1):
        while True:
            result = await use_case.get_snapshot()
            if not result.refresh_in_progress:
                return result
            await asyncio.sleep(0.001)


class SlaStatusUseCaseTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.source = AsyncMock(spec=SlaDigestSourcePort)
        self.source.fetch_entries.return_value = (entry(),)
        self.clock = Mock(return_value=0.0)
        self.now = Mock(return_value=datetime(2026, 10, 21, 14, 30, tzinfo=KST))
        self.use_case = SlaStatusUseCase(self.source, clock=self.clock, now=self.now)
        self.addAsyncCleanup(self.use_case.aclose)

    async def test_strict_remaining_ratio_boundary_and_positive_goal(self) -> None:
        self.source.fetch_entries.return_value = (
            entry("TACEA-0", remaining_millis=0),
            entry("TACEA-1", remaining_millis=29_999),
            entry("TACEA-2", remaining_millis=30_000),
            entry("TACEA-3", remaining_millis=30_001),
            entry("TACEA-4", remaining_millis=-1),
            entry("TACEA-5", goal_millis=0, remaining_millis=0),
            entry("TACEA-6", goal_millis=-1, remaining_millis=0),
        )
        result = await self.use_case.get_snapshot()
        self.assertEqual(["TACEA-0", "TACEA-1"], [ticket.key for ticket in result.tickets])
        self.assertEqual((2, 2, 30), (result.ticket_count, result.sla_count, result.threshold_percent))
        self.assertEqual(29.999, result.tickets[1].slas[0].remaining_percent)
        self.assertEqual(self.now.return_value, result.generated_at)

    async def test_groups_multiple_qualifying_slas_and_preserves_pause_metadata(self) -> None:
        self.source.fetch_entries.return_value = (
            entry(sla_id="customfield_10002", sla_name="해결", remaining_millis=10_000, paused=True),
            entry(), entry(sla_id="customfield_10003", remaining_millis=80_000),
        )
        result = await self.use_case.get_snapshot()
        self.assertEqual((1, 2), (result.ticket_count, result.sla_count))
        ticket = result.tickets[0]
        self.assertEqual(("점검 요청", "자료 요청 중", "담당자"), (ticket.summary, ticket.status, ticket.assignee))
        self.assertEqual(["customfield_10002", "customfield_10001"], [sla.sla_id for sla in ticket.slas])
        self.assertTrue(ticket.slas[0].paused)
        self.assertFalse(ticket.slas[1].paused)

    async def test_any_completed_or_current_breach_excludes_all_slas_on_ticket(self) -> None:
        entries = [entry("TACEA-4")]
        for key, breach in (
            ("TACEA-1", {"breached": True}),
            ("TACEA-2", {"issue_has_breached_sla": True}),
            ("TACEA-3", {"remaining_millis": -1}),
        ):
            entries.extend((entry(key), entry(key, sla_id="customfield_10002", **breach)))
        self.source.fetch_entries.return_value = tuple(entries)
        result = await self.use_case.get_snapshot()
        self.assertEqual(["TACEA-4"], [ticket.key for ticket in result.tickets])

    async def test_duplicate_sla_uses_last_value_without_inflating_counts(self) -> None:
        self.source.fetch_entries.return_value = (
            entry(remaining_millis=100), entry(remaining_millis=200),
            entry(sla_id="customfield_10002", remaining_millis=500),
            entry(sla_id="customfield_10002", remaining_millis=30_000),
        )
        result = await self.use_case.get_snapshot()
        self.assertEqual((1, 1), (result.ticket_count, result.sla_count))
        self.assertEqual(200, result.tickets[0].slas[0].remaining_millis)

    async def test_duplicate_with_any_breach_does_not_restore_ticket(self) -> None:
        self.source.fetch_entries.return_value = (entry(breached=True), entry())
        result = await self.use_case.get_snapshot()
        self.assertEqual((0, 0, ()), (result.ticket_count, result.sla_count, result.tickets))

    async def test_orders_by_ratio_then_remaining_millis_then_key(self) -> None:
        self.source.fetch_entries.return_value = (
            entry("TACEA-4", goal_millis=1000, remaining_millis=100),
            entry("TACEA-3", goal_millis=2000, remaining_millis=100),
            entry("TACEA-2", goal_millis=1000, remaining_millis=50),
            entry("TACEA-1", goal_millis=1000, remaining_millis=50),
        )
        result = await self.use_case.get_snapshot()
        self.assertEqual(["TACEA-1", "TACEA-2", "TACEA-3", "TACEA-4"], [t.key for t in result.tickets])

    async def test_empty_success_is_timestamped_and_cached(self) -> None:
        self.source.fetch_entries.return_value = ()
        result = await self.use_case.get_snapshot()
        self.assertEqual((0, 0, ()), (result.ticket_count, result.sla_count, result.tickets))
        self.assertEqual(self.now.return_value, result.generated_at)
        self.assertIs(result, await self.use_case.get_snapshot())
        self.source.fetch_entries.assert_awaited_once_with()

    async def test_cache_expires_at_sixty_seconds_without_adjusting_sla_values(self) -> None:
        result = await self.use_case.get_snapshot()
        self.clock.return_value = 59.999
        self.assertIs(result, await self.use_case.get_snapshot())
        self.assertEqual(20_000, result.tickets[0].slas[0].remaining_millis)
        self.clock.return_value = 60
        self.now.return_value = datetime(2026, 10, 21, 14, 31, tzinfo=KST)
        refreshed = await self.use_case.get_snapshot()
        self.assertTrue(refreshed.refresh_in_progress)
        self.assertTrue(refreshed.stale)
        self.assertEqual(result.tickets, refreshed.tickets)
        completed = await wait_for_refresh(self.use_case)
        self.assertEqual(self.now.return_value, completed.generated_at)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_refresh_ignores_cache_and_simultaneous_requests_share_collection(self) -> None:
        cached = await self.use_case.get_snapshot()
        started, release = asyncio.Event(), asyncio.Event()

        async def collect():
            started.set()
            await release.wait()
            return (entry(remaining_millis=1000),)

        self.source.fetch_entries.side_effect = collect
        first = asyncio.create_task(self.use_case.get_snapshot(refresh=True))
        await started.wait()
        second = asyncio.create_task(self.use_case.get_snapshot(refresh=True))
        third = asyncio.create_task(self.use_case.get_snapshot())
        await asyncio.sleep(0)
        results = await asyncio.gather(first, second, third)
        self.assertTrue(all(result.refresh_in_progress for result in results))
        self.assertTrue(all(result.tickets == cached.tickets for result in results))
        release.set()
        completed = await wait_for_refresh(self.use_case)
        self.assertEqual(1000, completed.tickets[0].slas[0].remaining_millis)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_collection_failure_is_shared_and_not_cached_as_empty(self) -> None:
        started, release = asyncio.Event(), asyncio.Event()

        async def fail():
            started.set()
            await release.wait()
            raise RuntimeError("upstream private details")

        self.source.fetch_entries.side_effect = fail
        first = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        second = asyncio.create_task(self.use_case.get_snapshot())
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        self.assertTrue(all(isinstance(result, SlaStatusSourceError) for result in results))
        self.assertTrue(all("private" not in str(result) for result in results))
        self.assertEqual(1, self.source.fetch_entries.await_count)
        self.source.fetch_entries.side_effect = None
        self.assertEqual(1, (await self.use_case.get_snapshot()).ticket_count)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_failed_refresh_keeps_saved_result_and_reports_error(self) -> None:
        cached = await self.use_case.get_snapshot()
        self.source.fetch_entries.side_effect = RuntimeError("Jira unavailable")
        pending = await self.use_case.get_snapshot(refresh=True)
        self.assertTrue(pending.refresh_in_progress)
        completed = await wait_for_refresh(self.use_case)
        self.assertEqual(cached.tickets, completed.tickets)
        self.assertTrue(completed.stale)
        self.assertIsNotNone(completed.refresh_error)
        self.assertNotIn("Jira unavailable", completed.refresh_error)

    async def test_total_deadline_cancels_source_preserves_cache_and_allows_new_retry(self) -> None:
        use_case = SlaStatusUseCase(self.source, clock=self.clock, now=self.now, timeout_seconds=0.02)
        self.addAsyncCleanup(use_case.aclose)
        cached = await use_case.get_snapshot()
        cancelled = asyncio.Event()

        async def slow_source():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.source.fetch_entries.side_effect = slow_source
        pending = await asyncio.wait_for(use_case.get_snapshot(refresh=True), 0.5)
        self.assertEqual(cached.tickets, pending.tickets)
        completed = await wait_for_refresh(use_case)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(cached.tickets, completed.tickets)
        self.assertIsNotNone(completed.refresh_error)
        self.source.fetch_entries.side_effect = None
        await use_case.get_snapshot(refresh=True)
        self.assertIsNone((await wait_for_refresh(use_case)).refresh_error)
        self.assertEqual(3, self.source.fetch_entries.await_count)

    def test_collection_timeout_must_be_positive(self) -> None:
        for value in (0, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SlaStatusUseCase(self.source, timeout_seconds=value)

    async def test_cancelled_waiter_does_not_cancel_other_waiters(self) -> None:
        started, release, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def collect():
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return (entry(),)

        self.source.fetch_entries.side_effect = collect
        first = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        second = asyncio.create_task(self.use_case.get_snapshot(refresh=True))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(cancelled.is_set())
        release.set()
        self.assertEqual(1, (await second).ticket_count)
        self.source.fetch_entries.assert_awaited_once_with()

    async def test_last_waiter_cancellation_stops_collection_and_allows_retry(self) -> None:
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def collect():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.source.fetch_entries.side_effect = collect
        task = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cancelled.is_set())
        self.source.fetch_entries.side_effect = None
        self.assertEqual(1, (await self.use_case.get_snapshot()).ticket_count)

    async def test_privacy_clear_removes_cached_people_and_remains_usable(self) -> None:
        previous = await self.use_case.get_snapshot()
        await self.use_case.clear_personal_data_cache()
        self.source.fetch_entries.return_value = (entry(assignee="새 담당자"),)
        result = await self.use_case.get_snapshot()
        self.assertIsNot(previous, result)
        self.assertEqual("새 담당자", result.tickets[0].assignee)
        self.assertEqual(2, self.source.fetch_entries.await_count)
        self.source.aclose.assert_not_awaited()

    async def test_privacy_clear_prevents_late_source_result_repopulating_cache(self) -> None:
        started = asyncio.Event()

        async def ignore_cancel():
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return (entry(assignee="지워진 담당자"),)

        self.source.fetch_entries.side_effect = ignore_cancel
        task = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        await self.use_case.clear_personal_data_cache()
        with self.assertRaises(SlaStatusSourceError):
            await task
        self.source.fetch_entries.side_effect = None
        result = await self.use_case.get_snapshot()
        self.assertEqual("담당자", result.tickets[0].assignee)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_close_cancels_active_collection_without_closing_shared_source(self) -> None:
        started = asyncio.Event()

        async def collect():
            started.set()
            await asyncio.Event().wait()

        self.source.fetch_entries.side_effect = collect
        task = asyncio.create_task(self.use_case.get_snapshot())
        await started.wait()
        await self.use_case.aclose()
        await self.use_case.aclose()
        with self.assertRaises(asyncio.CancelledError):
            await task
        with self.assertRaises(SlaStatusSourceError):
            await self.use_case.get_snapshot()
        self.source.aclose.assert_not_awaited()


class SlaStatusDetailsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.source = AsyncMock(spec=SlaDigestSourcePort)
        self.source.fetch_entries.return_value = (entry(goal_millis=9_000_000, remaining_millis=1_800_000),)
        self.details = AsyncMock(spec=SlaStatusDetailsPort)
        self.details.fetch_details.return_value = (detailed_issue(),)
        self.now = Mock(return_value=datetime(2026, 10, 21, 11, tzinfo=KST))
        self.use_case = SlaStatusUseCase(self.source, self.details, now=self.now)
        self.addAsyncCleanup(self.use_case.aclose)

    async def test_shared_sla_clock_enriches_current_status_and_public_metadata(self) -> None:
        result = await self.use_case.get_snapshot()
        self.details.fetch_details.assert_awaited_once_with(("TACEA-1",))
        ticket = result.tickets[0]
        self.assertEqual("검토 중", ticket.status)
        self.assertEqual(("최신 점검 요청", "고객사", ("파트너사",), "보고자", "새 담당자", "TAC 담당자", "인시던트"), (
            ticket.summary, ticket.customer, ticket.partners, ticket.reporter, ticket.assignee, ticket.tac_assignee, ticket.issue_type,
        ))
        self.assertEqual(datetime(2026, 10, 21, 9, tzinfo=KST), ticket.created_at)
        self.assertEqual(0, ticket.elapsed_days)
        self.assertEqual("resolution_sla", ticket.status_durations_basis)
        self.assertEqual("평일 9~18", ticket.status_duration_calendar)
        self.assertEqual({"할 일": 1, "검토 중": 1}, {value.status: value.hours for value in ticket.status_durations})
        self.assertEqual((), ticket.warnings)
        encoded = SlaStatusSnapshotSchema.model_validate(result).model_dump_json()
        for private in ("account_id", "private-reporter-id", "private-assignee-id", "private-tac-id", "personal_data_retrieved_at"):
            self.assertNotIn(private, encoded)

    async def test_incomplete_history_is_unknown_with_warning_instead_of_zero(self) -> None:
        self.details.fetch_details.return_value = (detailed_issue(history_complete=False),)
        ticket = (await self.use_case.get_snapshot()).tickets[0]
        self.assertIsNone(ticket.status_durations)
        self.assertIsNone(ticket.status_duration_calendar)
        self.assertTrue(any("불완전" in warning for warning in ticket.warnings))

    async def test_missing_calendar_is_unknown_with_warning(self) -> None:
        self.details.fetch_details.return_value = (detailed_issue(clock_calendars=()),)
        ticket = (await self.use_case.get_snapshot()).tickets[0]
        self.assertIsNone(ticket.status_durations)
        self.assertTrue(ticket.warnings)

    async def test_details_only_receive_qualified_unique_keys_and_ignore_unrequested_issues(self) -> None:
        self.source.fetch_entries.return_value = (
            entry(), entry(sla_id="customfield_10002"), entry("TACEA-2", remaining_millis=30_000),
        )
        self.details.fetch_details.return_value = (detailed_issue(), detailed_issue("TACEA-99"))
        result = await self.use_case.get_snapshot()
        self.assertEqual((1, 2), (result.ticket_count, result.sla_count))
        self.details.fetch_details.assert_awaited_once_with(("TACEA-1",))

    async def test_missing_current_ticket_is_excluded(self) -> None:
        self.details.fetch_details.return_value = ()
        result = await self.use_case.get_snapshot()
        self.assertEqual((0, 0, ()), (result.ticket_count, result.sla_count, result.tickets))

    async def test_newly_breached_or_changed_license_ticket_is_excluded(self) -> None:
        base = detailed_issue()
        for issue in (
            replace(base, cycles=(replace(base.cycles[0], breached=True),)),
            replace(base, cycles=(replace(base.cycles[0], ongoing=False, breached=True),)),
            replace(base, cycles=(replace(base.cycles[0], elapsed_ms=10_000_000),)),
            replace(base, issue_type="라이선스"),
        ):
            with self.subTest(issue=issue.key):
                self.details.fetch_details.return_value = (issue,)
                await self.use_case.get_snapshot(refresh=True)
                result = await wait_for_refresh(self.use_case)
                self.assertEqual((0, 0), (result.ticket_count, result.sla_count))

    async def test_details_failure_fails_whole_snapshot_and_can_retry(self) -> None:
        self.details.fetch_details.side_effect = RuntimeError("private data")
        with self.assertRaises(SlaStatusSourceError) as error:
            await self.use_case.get_snapshot()
        self.assertNotIn("private", str(error.exception))
        self.details.fetch_details.side_effect = None
        self.assertEqual(1, (await self.use_case.get_snapshot()).ticket_count)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_total_deadline_includes_waiting_for_detail_collection(self) -> None:
        use_case = SlaStatusUseCase(self.source, self.details, timeout_seconds=0.02)
        self.addAsyncCleanup(use_case.aclose)
        cancelled = asyncio.Event()

        async def slow_details(keys):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.details.fetch_details.side_effect = slow_details
        with self.assertRaises(SlaStatusSourceError) as error:
            await asyncio.wait_for(use_case.get_snapshot(), 0.5)
        self.assertIsInstance(error.exception.__cause__, TimeoutError)
        self.assertTrue(cancelled.is_set())
        self.details.fetch_details.side_effect = None
        self.assertEqual(1, (await use_case.get_snapshot()).ticket_count)
        self.assertEqual(2, self.source.fetch_entries.await_count)

    async def test_no_matches_skip_details_and_result_time_is_after_details_collection(self) -> None:
        self.now.side_effect = [datetime(2026, 10, 21, 11, tzinfo=KST), datetime(2026, 10, 21, 11, 1, tzinfo=KST)]
        result = await self.use_case.get_snapshot()
        self.assertEqual(datetime(2026, 10, 21, 11, 1, tzinfo=KST), result.generated_at)
        self.source.fetch_entries.return_value = ()
        self.now.side_effect = None
        await self.use_case.get_snapshot(refresh=True)
        result = await wait_for_refresh(self.use_case)
        self.assertEqual(0, result.ticket_count)
        self.assertEqual(1, self.details.fetch_details.await_count)


class SlaStatusSourcePolicyTest(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_ongoing_cycles_license_done_and_any_breach_exclusions(self) -> None:
        def cycle(remaining=20_000, **overrides):
            return {
                "paused": False, "breached": remaining < 0,
                "goalDuration": {"millis": 100_000}, "remainingTime": {"millis": remaining},
                **overrides,
            }

        def issue(key, **overrides):
            return {"key": key, "fields": {
                "summary": "점검", "status": {"name": "진행", "statusCategory": {"key": "indeterminate"}},
                "assignee": None, "issuetype": {"name": "인시던트"},
                "customfield_10001": {"ongoingCycle": cycle()}, "customfield_10002": None,
                **overrides,
            }}

        issues = [
            issue("TACEA-1", customfield_10001={"ongoingCycle": cycle(29_999, paused=True)}),
            issue("TACEA-2", customfield_10001={"ongoingCycle": cycle(30_000)}),
            issue("TACEA-3", issuetype={"name": "라이선스"}),
            issue("TACEA-4", status={"name": "완료", "statusCategory": {"key": "done"}}),
            issue("TACEA-5", customfield_10002={"completedCycles": [{"breached": True}]}),
            issue("TACEA-6", customfield_10002={"ongoingCycle": cycle(-1)}),
            issue("TACEA-7", customfield_10001={"completedCycles": [{"breached": False}]}),
        ]

        def respond(request):
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=[{
                    "id": identifier, "name": "SLA", "schema": {"custom": "com.atlassian.servicedesk:sd-sla-field"},
                } for identifier in ("customfield_10001", "customfield_10002")])
            return httpx.Response(200, json={"issues": issues, "isLast": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            async with SlaDigestJiraSource("https://jira.example.test", "user", "token", client=client) as source:
                use_case = SlaStatusUseCase(source)
                try:
                    result = await use_case.get_snapshot()
                finally:
                    await use_case.aclose()
        self.assertEqual(["TACEA-1"], [ticket.key for ticket in result.tickets])
        self.assertEqual("미지정", result.tickets[0].assignee)
        self.assertTrue(result.tickets[0].slas[0].paused)
