# backend/tests/test_personal_data_runtime.py
import asyncio
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.application.ports.personal_data_port import PersonalDataReportingFailure, PersonalDataRepositoryPort
from src.application.services.personal_data_reporting_service import PersonalDataReportingService
from src.application.use_cases.report_personal_data import ReportPersonalDataUseCase
from src.domain.entities.personal_data import PersonalDataAction
from src.infrastructure.personal_data_runtime import PersonalDataSnapshots, PostgresPersonalDataReportingLock


NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)


class FakeDatabase:
    def __init__(self):
        self.connection = AsyncMock()
        self.connection.scalar.return_value = True
        self.events = []

    @asynccontextmanager
    async def session(self):
        self.events.append("session_open")
        try:
            yield self.connection
        except BaseException:
            self.events.append("session_rolled_back")
            raise
        else:
            self.events.append("session_committed")


def status(**changes):
    return {
        "owner_authorized": True, "registered_accounts": 2,
        "account_states": {"active": 1, "closed": 1},
        "unreported_accounts": 0, "due_accounts": 0,
        "next_attempt_at": None, "last_success_at": (NOW - timedelta(days=1)).isoformat(),
        "last_error": None, **changes,
    }


class FakeReportingLock:
    def __init__(self):
        self.available = True
        self.events = []

    @asynccontextmanager
    async def acquire(self):
        self.events.append("acquire")
        try:
            yield self.available
        finally:
            self.events.append("release")


class PersonalDataReportingServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.current_status = status()
        self.repository = AsyncMock(spec=PersonalDataRepositoryPort)
        self.repository.status.side_effect = lambda: dict(self.current_status)
        self.repository.pending_actions.return_value = ()
        self.snapshots = AsyncMock()
        self.snapshots.collect_accounts.return_value = ()
        self.snapshots.coverage.return_value = {"known_accounts": 1, "unmapped_personal_fields": 0}
        self.use_case = AsyncMock()
        self.use_case.erase_pending.return_value = 0
        self.use_case.execute.return_value = {"reported_accounts": 0, "erased_report_rows": 0}
        self.reporting_lock = FakeReportingLock()
        self.runtime = PersonalDataReportingService(
            self.repository, self.snapshots, self.use_case, self.reporting_lock,
        )
        self.clock = patch("src.application.services.personal_data_reporting_service.datetime")
        self.mock_clock = self.clock.start()
        self.mock_clock.now.return_value = NOW
        self.mock_clock.fromisoformat.side_effect = datetime.fromisoformat
        self.addCleanup(self.clock.stop)

    async def test_updated_and_pending_states_are_not_reporting_ready(self):
        for state in ("updated", "pending_updated", "pending_closed"):
            with self.subTest(state=state):
                self.current_status["account_states"] = {state: 1}
                self.assertFalse((await self.runtime.reporting_status())["reporting_ready"])
        self.current_status["account_states"] = {"active": 1, "closed": 1}
        self.assertTrue((await self.runtime.reporting_status())["reporting_ready"])

    async def test_successful_retry_clears_all_profile_and_processing_errors_without_changing_reporting_cycle(self):
        for code in ("invalid_profile_response", "invalid_profile_account", "profile_access_unavailable", "reporting_processing_failed"):
            with self.subTest(code=code):
                self.repository.reset_mock()
                self.current_status.update(last_error=code, next_attempt_at=(NOW - timedelta(minutes=1)).isoformat())
                result = await self.runtime.run_reporting()
                self.assertEqual("ok", result["status"])
                self.repository.record_attempt.assert_awaited_once_with(NOW)
                self.repository.mark_reported.assert_not_awaited()
                self.repository.record_result.assert_not_awaited()

    async def test_partially_completed_profile_batch_keeps_error_until_remaining_accounts_finish(self):
        self.current_status.update(last_error="invalid_profile_response", account_states={"active": 90, "updated": 5})
        self.use_case.execute.return_value = {"reported_accounts": 90, "erased_report_rows": 0}
        self.assertEqual("ok", (await self.runtime.run_reporting())["status"])
        self.repository.record_attempt.assert_not_awaited()
        self.assertFalse((await self.runtime.reporting_status())["reporting_ready"])

    async def test_successful_reporting_is_recorded_but_idle_success_does_not_rewrite_status(self):
        self.assertEqual("ok", (await self.runtime.run_reporting())["status"])
        self.repository.record_attempt.assert_not_awaited()
        self.use_case.execute.return_value = {"reported_accounts": 1, "erased_report_rows": 0}
        self.assertEqual("ok", (await self.runtime.run_reporting())["status"])
        self.repository.record_attempt.assert_awaited_once_with(NOW)

    async def test_backoff_masks_closed_and_updated_without_any_profile_or_reporting_request(self):
        deadline = (NOW + timedelta(minutes=30)).isoformat()
        self.current_status.update(last_error="profile_rate_limited", next_attempt_at=deadline)
        closed = PersonalDataAction("closed", "closed")
        updated = PersonalDataAction("changed", "updated")
        self.repository.pending_actions.return_value = (updated, closed)
        self.snapshots.erase_personal_data.return_value = 2
        self.snapshots.mark_personal_data_updated.return_value = 1
        reporter, profiles = AsyncMock(), AsyncMock()
        self.runtime._use_case = ReportPersonalDataUseCase(self.repository, reporter, self.snapshots, profiles)
        self.assertEqual({"status": "retry_scheduled", "next_attempt_at": deadline}, await self.runtime.run_reporting())
        self.snapshots.erase_personal_data.assert_awaited_once_with(("closed",))
        self.snapshots.mark_personal_data_updated.assert_awaited_once_with(("changed",))
        self.assertEqual([(closed,), (updated,)], [call.args[0] for call in self.repository.finish_actions.await_args_list])
        profiles.get_profile.assert_not_awaited()
        reporter.report.assert_not_awaited()
        self.repository.record_attempt.assert_not_awaited()
        self.repository.register_accounts.assert_not_awaited()

    async def test_storage_failure_during_backoff_never_shortens_provider_retry_deadline(self):
        deadline = NOW + timedelta(minutes=30)
        self.current_status.update(last_error="profile_rate_limited", next_attempt_at=deadline.isoformat())
        self.use_case.erase_pending.side_effect = RuntimeError("private database details")
        self.assertEqual({"status": "reporting_processing_failed"}, await self.runtime.run_reporting())
        self.use_case.erase_pending.assert_awaited_once_with(refresh_profiles=False)
        self.repository.record_attempt.assert_awaited_once_with(NOW, error="reporting_processing_failed", next_attempt_at=deadline)
        self.use_case.execute.assert_not_awaited()

    async def test_provider_failure_records_exact_retry_deadline_and_does_not_record_success(self):
        self.use_case.erase_pending.side_effect = PersonalDataReportingFailure("profile_rate_limited", 1800)
        result = await self.runtime.run_reporting()
        deadline = NOW + timedelta(minutes=30)
        self.assertEqual({"status": "profile_rate_limited", "next_attempt_at": deadline.isoformat()}, result)
        self.repository.record_attempt.assert_awaited_once_with(NOW, error="profile_rate_limited", next_attempt_at=deadline)
        self.use_case.execute.assert_not_awaited()

    async def test_cancellation_propagates_without_error_state_or_success_record(self):
        self.use_case.erase_pending.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await self.runtime.run_reporting()
        self.repository.record_attempt.assert_not_awaited()
        self.assertFalse(self.runtime._lock.locked())

    async def test_unavailable_reporting_lock_never_calls_repository_or_use_case(self):
        self.reporting_lock.available = False
        self.assertEqual({"status": "already_running"}, await self.runtime.run_reporting())
        self.repository.status.assert_not_awaited()
        self.use_case.erase_pending.assert_not_awaited()
        self.assertEqual(["acquire", "release"], self.reporting_lock.events)

    async def test_local_concurrent_call_returns_without_acquiring_second_database_lock(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def erase_pending(**kwargs):
            entered.set()
            await release.wait()
            return 0

        self.use_case.erase_pending.side_effect = erase_pending
        running = asyncio.create_task(self.runtime.run_reporting())
        await entered.wait()
        self.assertEqual({"status": "already_running"}, await self.runtime.run_reporting())
        self.assertEqual(["acquire"], self.reporting_lock.events)
        release.set()
        self.assertEqual("ok", (await running)["status"])
        self.assertEqual(["acquire", "release"], self.reporting_lock.events)

    async def test_missing_owner_still_processes_erasure_and_account_inventory(self):
        self.current_status["owner_authorized"] = False
        self.assertEqual({"status": "owner_authorization_required"}, await self.runtime.run_reporting())
        self.use_case.erase_pending.assert_awaited_once_with(refresh_profiles=True)
        self.snapshots.collect_accounts.assert_awaited_once_with()
        self.repository.register_accounts.assert_awaited_once_with(())
        self.use_case.execute.assert_not_awaited()

    async def test_grant_errors_hide_details_and_release_local_lock(self):
        for error, expected in (
            (ValueError("private account"), "owner_grant_configuration_invalid"),
            (RuntimeError("private database"), "owner_grant_storage_failed"),
        ):
            self.repository.save_reporting_grant.side_effect = error
            with self.assertRaises(PersonalDataReportingFailure) as raised:
                await self.runtime.save_reporting_grant("owner", "private-token")
            self.assertEqual(expected, raised.exception.code)
            self.assertFalse(self.runtime._lock.locked())

    async def test_profile_access_delegates_to_injected_repository(self):
        identity = object()
        self.repository.register_identity.return_value = identity
        self.repository.resolve_identity.return_value = identity
        self.assertIs(identity, await self.runtime.register_identity(identity))
        self.assertIs(identity, await self.runtime.resolve_identity(identity))
        self.repository.register_identity.assert_awaited_once_with(identity)
        self.repository.resolve_identity.assert_awaited_once_with(identity)


class PersonalDataReportingLockTest(unittest.IsolatedAsyncioTestCase):
    async def test_advisory_lock_lives_until_context_finishes(self):
        database = FakeDatabase()
        lock = PostgresPersonalDataReportingLock(database)
        async with lock.acquire() as acquired:
            self.assertTrue(acquired)
            self.assertEqual(["session_open"], database.events)
        self.assertEqual(["session_open", "session_committed"], database.events)
        statement = database.connection.scalar.call_args.args[0]
        self.assertEqual("SELECT pg_try_advisory_xact_lock(20261016, 1900)", str(statement))

    async def test_failed_lock_and_cancelled_body_release_database_session(self):
        database = FakeDatabase()
        database.connection.scalar.return_value = False
        lock = PostgresPersonalDataReportingLock(database)
        async with lock.acquire() as acquired:
            self.assertFalse(acquired)
        self.assertEqual("session_committed", database.events[-1])
        database.connection.scalar.return_value = True
        with self.assertRaises(asyncio.CancelledError):
            async with lock.acquire():
                raise asyncio.CancelledError
        self.assertEqual("session_rolled_back", database.events[-1])


class PersonalDataSnapshotCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_closed_or_updated_masks_without_changes_do_not_clear_every_login_grant(self):
        database = FakeDatabase()
        clear = AsyncMock()
        store = AsyncMock()
        store.erase_personal_data.return_value = 0
        store.mark_personal_data_updated.return_value = 0
        snapshots = PersonalDataSnapshots(database, clear)
        with patch("src.infrastructure.personal_data_runtime.PersonalDataSnapshotStore", return_value=store):
            for _ in range(2):
                self.assertEqual(0, await snapshots.erase_personal_data(("closed",)))
                self.assertEqual(0, await snapshots.mark_personal_data_updated(("updated",)))
        clear.assert_not_awaited()

    async def test_changed_masks_clear_cache_only_after_snapshot_commit(self):
        database = FakeDatabase()
        async def clear():
            self.assertEqual("session_committed", database.events[-1])
            database.events.append("cleared")
        store = AsyncMock()
        store.erase_personal_data.return_value = 1
        store.mark_personal_data_updated.return_value = 2
        snapshots = PersonalDataSnapshots(database, clear)
        with patch("src.infrastructure.personal_data_runtime.PersonalDataSnapshotStore", return_value=store):
            self.assertEqual(1, await snapshots.erase_personal_data(("closed",)))
            self.assertEqual(2, await snapshots.mark_personal_data_updated(("updated",)))
        self.assertEqual(2, database.events.count("cleared"))
