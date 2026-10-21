# backend/tests/test_personal_data_repository.py
import asyncio
import os
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from jose import jwt
from sqlalchemy import delete, event, select, update
from unittest.mock import AsyncMock, patch

from src.application.ports.personal_data_port import PersonalDataReportingFailure
from src.domain.entities.auth_identity import AuthIdentity
from src.application.services.snapshot_personal_data import REDACTED_PERSON, UPDATING_PERSON, snapshot_people
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction, PersonalDataProfile
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM, PersonalDataGrantORM
from src.infrastructure.persistence.personal_data_repository import PersonalDataRepository
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore
from src.infrastructure.persistence.models import ReportORM
from src.infrastructure.persistence.sla_violation_models import SlaViolationReportORM
from src.infrastructure.persistence.redeployment_repository_impl import RedeploymentReportORM
from src.infrastructure.persistence.issue_management_snapshot_repository import IssueManagementSnapshotORM
from src.infrastructure.persistence.sla_status_snapshot_repository import SlaStatusSnapshotORM
from src.infrastructure.security.jwt_service import JwtService

DATABASE_URL = os.environ.get("PERSONAL_DATA_TEST_DATABASE_URL")
SECRET = "personal-data-tests-only-server-key-with-32-bytes"


class PersonalDataEmailContractTest(unittest.TestCase):
    def test_existing_positional_identity_and_profile_arguments_remain_compatible(self):
        identity = AuthIdentity("jira:site:account-1", "사용자", "jira", 9999999999, 2, "g" * 43)
        profile = PersonalDataProfile("account-1", "사용자", datetime.now(timezone.utc))
        self.assertEqual("g" * 43, identity.jira_grant_id)
        self.assertIsNone(identity.email_address)
        self.assertIsNone(profile.email_address)

    def test_access_and_refresh_tokens_omit_email_and_keep_opaque_grant(self):
        service = JwtService(SimpleNamespace(jwt_secret=SECRET, jwt_access_expire_minutes=30, jwt_refresh_expire_days=7, login=False))
        identity = AuthIdentity("jira:site:account-1", "사용자", "jira", 9999999999, 2, "g" * 43, "verified@example.com")
        for create, decode in ((service.create_identity_access_token, service.decode_access_identity), (service.create_identity_refresh_token, service.decode_refresh_identity)):
            with self.subTest(token=create.__name__):
                token = create(identity)
                payload = jwt.get_unverified_claims(token)
                self.assertNotIn("email_address", payload)
                self.assertNotIn(identity.email_address, str(payload))
                restored = decode(token)
                self.assertEqual((identity.username, identity.jira_grant_id, identity.profile_version), (restored.username, restored.jira_grant_id, restored.profile_version))
                self.assertIsNone(restored.email_address)


@unittest.skipUnless(DATABASE_URL, "Requires an isolated PostgreSQL PERSONAL_DATA_TEST_DATABASE_URL")
class PersonalDataRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = Database(DATABASE_URL)
        self.repository = PersonalDataRepository(self.database, SECRET, "owner")
        self.identity = AuthIdentity("jira:site:account-1", "김영준", "jira", 9999999999)
        self.snapshot_rows = []
        async with self.database.session() as session:
            await session.execute(delete(PersonalDataAccountORM))
            await session.execute(delete(PersonalDataGrantORM))

    async def asyncTearDown(self):
        async with self.database.session() as session:
            for model, row_id in self.snapshot_rows:
                await session.execute(delete(model).where(model.id == row_id))
        await self.database.aclose()

    async def _save_snapshots(self, payload, generated_at):
        rows = [
            ReportORM(week_start=generated_at.date(), week_end=generated_at.date(), report_date=str(generated_at.date()), created_at=generated_at, widgets=deepcopy(payload)),
            SlaViolationReportORM(period="month", selected_date=generated_at.date(), start_date=generated_at.date(), end_date=generated_at.date(), generated_at=generated_at, generated_by="privacy-test", ticket_count=1, initial_response_count=1, resolution_count=0, payload=deepcopy(payload)),
            RedeploymentReportORM(snapshot_date=generated_at.date(), generated_at=generated_at, generated_by="privacy-test", payload=deepcopy(payload)),
            IssueManagementSnapshotORM(project_key="PRIVACY-REFRESH-TEST", synced_at=generated_at, full_synced_at=generated_at, payload=deepcopy(payload)),
            SlaStatusSnapshotORM(project_key="PRIVACY-REFRESH-TEST", generated_at=generated_at, payload=deepcopy(payload)),
        ]
        async with self.database.session() as session:
            for row in rows:
                session.add(row)
            await session.flush()
            self.snapshot_rows.extend((type(row), row.id) for row in rows)
        return rows

    async def test_login_email_comes_from_verified_identity_and_resolves_from_current_database(self):
        verified = replace(self.identity, jira_grant_id="g" * 43, email_address="first@example.com")
        registered = await self.repository.register_identity(verified)
        self.assertEqual("first@example.com", registered.email_address)
        self.assertEqual((verified.username, verified.jira_grant_id), (registered.username, registered.jira_grant_id))
        self.assertEqual(registered, await self.repository.resolve_identity(replace(registered, email_address="untrusted@example.com")))
        changed = await self.repository.register_identity(replace(verified, email_address="current@example.com"))
        self.assertEqual("current@example.com", (await self.repository.resolve_identity(registered)).email_address)
        self.assertEqual(registered.profile_version, changed.profile_version)
        hidden = await self.repository.register_identity(replace(verified, email_address=None))
        self.assertIsNone(hidden.email_address)
        self.assertIsNone((await self.repository.resolve_identity(registered)).email_address)
        async with self.database.session() as session:
            self.assertIsNone((await session.get(PersonalDataAccountORM, "account-1")).email_address)

    async def test_privacy_staging_clears_email_for_both_actions_and_entry_points(self):
        now = datetime.now(timezone.utc)
        for entry_point in ("stage_actions", "record_result"):
            for status in ("updated", "closed"):
                with self.subTest(entry_point=entry_point, status=status):
                    account_id = f"{entry_point}-{status}"
                    identity = await self.repository.register_identity(replace(self.identity, username=f"jira:site:{account_id}", email_address="private@example.com"))
                    action = PersonalDataAction(account_id, status)
                    if entry_point == "record_result":
                        await self.repository.record_result((account_id,), (action,), now, now + timedelta(days=7))
                    else:
                        await self.repository.stage_actions((action,))
                    async with self.database.session() as session:
                        row = await session.get(PersonalDataAccountORM, account_id)
                        self.assertEqual(f"pending_{status}", row.status)
                        self.assertIsNone(row.email_address)
                    with self.assertRaises(ValueError):
                        await self.repository.resolve_identity(identity)
                    await self.repository.finish_actions((action,))
                    async with self.database.session() as session:
                        row = await session.get(PersonalDataAccountORM, account_id)
                        self.assertEqual(status, row.status)
                        self.assertIsNone(row.email_address)

    async def test_finish_actions_clears_email_from_existing_pending_rows(self):
        now = datetime.now(timezone.utc)
        actions = tuple(PersonalDataAction(status, status) for status in ("updated", "closed"))
        async with self.database.session() as session:
            for action in actions:
                session.add(PersonalDataAccountORM(account_id=action.account_id, email_address="private@example.com", oldest_retrieved_at=now, status=f"pending_{action.status}", profile_version=2))
        await self.repository.finish_actions(actions)
        async with self.database.session() as session:
            for action in actions:
                self.assertIsNone((await session.get(PersonalDataAccountORM, action.account_id)).email_address)

    async def test_refresh_updated_profiles_restores_all_snapshot_types_and_preserves_closed_accounts(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=40)
        payload = {"total": 4, "by_assignee": {REDACTED_PERSON: 2, UPDATING_PERSON: 1, "그대로": 1}, "latest_issues": [
            {"key": "PRIVACY-1", "assignee": REDACTED_PERSON, "assignee_account_id": "account-1", "reporter": "보고자", "reporter_account_id": "unrelated", "personal_data_retrieved_at": old.isoformat(), "hours": 8},
            {"key": "PRIVACY-2", "assignee": UPDATING_PERSON, "assignee_account_id": "account-2", "personal_data_retrieved_at": old.isoformat(), "hours": 4},
            {"key": "PRIVACY-3", "assignee": REDACTED_PERSON, "assignee_account_id": "closed", "hours": 2},
            {"key": "PRIVACY-4", "assignee": "그대로", "assignee_account_id": "active", "hours": 1},
        ]}
        rows = await self._save_snapshots(payload, old)
        async with self.database.session() as session:
            for account_id, status in (("account-1", "updated"), ("account-2", "pending_updated"), ("closed", "closed"), ("active", "active")):
                session.add(PersonalDataAccountORM(account_id=account_id, display_name=None, email_address="old@example.com" if status != "closed" else None, oldest_retrieved_at=old, profile_version=2, status=status, next_report_at=now + timedelta(days=7)))
        callbacks = []
        async def after_commit():
            async with self.database.session() as session:
                callbacks.append((await session.get(PersonalDataAccountORM, "account-1")).status)
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_profiles_refreshed=after_commit)
        profiles = tuple(PersonalDataProfile(account_id, name, now, None if account_id == "account-2" else "fresh@example.com") for account_id, name in (("account-1", "현재 이름"), ("account-2", "다른 이름"), ("closed", "복원 금지"), ("active", "변경 금지"), ("missing", "추가 금지")))
        self.assertEqual(2, await repository.apply_refreshed_profiles(profiles))
        self.assertEqual(["active"], callbacks)
        self.assertEqual(0, await repository.apply_refreshed_profiles(profiles))
        self.assertEqual(["active"], callbacks)
        async with self.database.session() as session:
            for row in rows:
                saved = await session.get(type(row), row.id)
                actual = saved.widgets if isinstance(saved, ReportORM) else saved.payload
                self.assertEqual(["현재 이름", "다른 이름", REDACTED_PERSON, "그대로"], [item["assignee"] for item in actual["latest_issues"]])
                self.assertEqual({"현재 이름": 1, "다른 이름": 1, REDACTED_PERSON: 1, "그대로": 1}, actual["by_assignee"])
                self.assertEqual([8, 4, 2, 1], [item["hours"] for item in actual["latest_issues"]])
                self.assertEqual(4, actual["total"])
                self.assertNotIn("fresh@example.com", str(actual))
                people = list(snapshot_people(actual, old))
                self.assertEqual([now], [person.retrieved_at for person in people if person.account_id == "account-1"])
                self.assertEqual([old], [person.retrieved_at for person in people if person.account_id == "unrelated"])
            account = await session.get(PersonalDataAccountORM, "account-1")
            self.assertEqual(("active", "현재 이름", now, 2, now + timedelta(days=7)), (account.status, account.display_name, account.oldest_retrieved_at, account.profile_version, account.next_report_at))
            self.assertEqual(now, account.profile_retrieved_at)
            self.assertEqual("fresh@example.com", account.email_address)
            self.assertIsNone((await session.get(PersonalDataAccountORM, "account-2")).email_address)
            self.assertIsNone((await session.get(PersonalDataAccountORM, "closed")).email_address)
            self.assertEqual("old@example.com", (await session.get(PersonalDataAccountORM, "active")).email_address)
            self.assertEqual("closed", (await session.get(PersonalDataAccountORM, "closed")).status)
            self.assertIsNone(await session.get(PersonalDataAccountORM, "missing"))

    async def test_refresh_without_snapshots_still_invalidates_cache_once_after_commit(self):
        old = datetime.now(timezone.utc) - timedelta(days=1)
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", oldest_retrieved_at=old, profile_version=2, status="updated"))
        callback = AsyncMock()
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_profiles_refreshed=callback)
        self.assertEqual(1, await repository.apply_refreshed_profiles((PersonalDataProfile("account-1", "현재", old + timedelta(hours=1)),)))
        callback.assert_awaited_once_with()

    async def test_mark_updated_relabels_legacy_snapshots_without_touching_closed_records(self):
        now = datetime.now(timezone.utc)
        payload = {"tickets": [
            {"key": "PRIVACY-1", "reporter": REDACTED_PERSON, "reporter_account_id": "account-1"},
            {"key": "PRIVACY-2", "reporter": REDACTED_PERSON, "reporter_account_id": "closed"},
        ]}
        rows = await self._save_snapshots(payload, now)
        async with self.database.session() as session:
            for account_id, status in (("account-1", "updated"), ("closed", "closed")):
                session.add(PersonalDataAccountORM(account_id=account_id, oldest_retrieved_at=now, profile_version=2, status=status))
        async with self.database.session() as session:
            store = PersonalDataSnapshotStore(session)
            self.assertEqual(5, await store.mark_personal_data_updated(("account-1", "closed")))
            self.assertEqual(0, await store.mark_personal_data_updated(("account-1", "closed")))
        async with self.database.session() as session:
            for row in rows:
                saved = await session.get(type(row), row.id)
                actual = saved.widgets if isinstance(saved, ReportORM) else saved.payload
                self.assertEqual([UPDATING_PERSON, REDACTED_PERSON], [item["reporter"] for item in actual["tickets"]])

    async def test_updated_login_restores_snapshot_and_invokes_callback_after_commit(self):
        now = datetime.now(timezone.utc)
        rows = await self._save_snapshots({"tickets": [{"key": "PRIVACY-1", "reporter": UPDATING_PERSON, "reporter_account_id": "account-1"}]}, now - timedelta(days=1))
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", oldest_retrieved_at=now - timedelta(days=1), profile_version=2, status="updated"))
        committed_names = []
        async def after_commit():
            async with self.database.session() as session:
                saved = await session.get(ReportORM, rows[0].id)
                committed_names.append(saved.widgets["tickets"][0]["reporter"])
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_profiles_refreshed=after_commit)
        identity = await repository.register_identity(replace(self.identity, display_name="로그인 최신 이름", email_address="current@example.com"))
        self.assertEqual(2, identity.profile_version)
        self.assertEqual("current@example.com", identity.email_address)
        self.assertEqual(identity, await repository.resolve_identity(replace(identity, email_address=None)))
        self.assertEqual(["로그인 최신 이름"], committed_names)
        await repository.register_identity(identity)
        self.assertEqual(["로그인 최신 이름"], committed_names)

    async def test_action_callback_runs_once_after_actual_profile_transition_even_without_snapshots(self):
        now = datetime.now(timezone.utc)
        await self.repository.register_identity(self.identity)
        observed = []
        async def staged():
            async with self.database.session() as session:
                observed.append((await session.get(PersonalDataAccountORM, "account-1")).status)
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_actions_staged=staged)
        action = PersonalDataAction("account-1", "updated")
        await repository.record_result(("account-1",), (action,), now, now + timedelta(days=7))
        self.assertEqual(["pending_updated"], observed)
        await repository.record_result(("account-1",), (action,), now, now + timedelta(days=7))
        await repository.finish_actions((action,))
        await repository.stage_actions((action,))
        self.assertEqual(["pending_updated"], observed)
        await repository.apply_refreshed_profiles((PersonalDataProfile("account-1", "현재", now),))
        closed = PersonalDataAction("account-1", "closed")
        await repository.stage_actions((closed,))
        self.assertEqual(["pending_updated", "pending_closed"], observed)
        await repository.finish_actions((closed,))
        await repository.stage_actions((closed,))
        await repository.pending_actions()
        self.assertEqual(["pending_updated", "pending_closed"], observed)

    async def test_stale_account_census_cannot_age_a_fully_refreshed_profile(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        await self._save_snapshots({"tickets": [{"key": "PRIVACY-1", "reporter": UPDATING_PERSON, "reporter_account_id": "account-1", "personal_data_retrieved_at": old.isoformat()}]}, old)
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", oldest_retrieved_at=old, profile_version=2, status="updated"))
        await self.repository.apply_refreshed_profiles((PersonalDataProfile("account-1", "현재 이름", now),))
        await self.repository.register_accounts((PersonalDataAccount("account-1", old),))
        async with self.database.session() as session:
            row = await session.get(PersonalDataAccountORM, "account-1")
            self.assertEqual(now, row.oldest_retrieved_at)
            self.assertEqual(now, row.profile_retrieved_at)

    async def test_real_older_snapshots_remain_in_retention_census_after_a_fresh_login(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        await self._save_snapshots({"tickets": [{"key": "PRIVACY-1", "reporter": "과거 이름", "reporter_account_id": "account-1", "personal_data_retrieved_at": old.isoformat()}]}, old)
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", display_name="현재 이름", oldest_retrieved_at=now, profile_retrieved_at=now, profile_version=1, status="active"))
        await self.repository.register_accounts((PersonalDataAccount("account-1", old),))
        async with self.database.session() as session:
            row = await session.get(PersonalDataAccountORM, "account-1")
            self.assertEqual(old, row.oldest_retrieved_at)
            self.assertEqual(now, row.profile_retrieved_at)

    async def test_snapshot_failure_rolls_back_profile_and_all_snapshot_changes(self):
        now = datetime.now(timezone.utc)
        payload = {"tickets": [{"key": "PRIVACY-1", "reporter": UPDATING_PERSON, "reporter_account_id": "account-1"}]}
        rows = await self._save_snapshots(payload, now - timedelta(days=1))
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", oldest_retrieved_at=now - timedelta(days=1), profile_version=2, status="updated"))
        original = PersonalDataSnapshotStore.refresh_personal_data
        async def fail_after_snapshot_write(store, profiles):
            await original(store, profiles)
            raise RuntimeError("snapshot write failed")
        callback = AsyncMock()
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_profiles_refreshed=callback)
        with patch.object(PersonalDataSnapshotStore, "refresh_personal_data", fail_after_snapshot_write):
            with self.assertRaisesRegex(RuntimeError, "snapshot write failed"):
                await repository.apply_refreshed_profiles((PersonalDataProfile("account-1", "현재", now, "fresh@example.com"),))
        callback.assert_not_awaited()
        async with self.database.session() as session:
            self.assertEqual("updated", (await session.get(PersonalDataAccountORM, "account-1")).status)
            self.assertIsNone((await session.get(PersonalDataAccountORM, "account-1")).email_address)
            for row in rows:
                saved = await session.get(type(row), row.id)
                self.assertEqual(payload, saved.widgets if isinstance(saved, ReportORM) else saved.payload)

    async def test_concurrently_closed_account_is_not_reactivated_after_row_lock_wait(self):
        now = datetime.now(timezone.utc)
        async with self.database.session() as session:
            session.add(PersonalDataAccountORM(account_id="account-1", oldest_retrieved_at=now - timedelta(days=1), profile_version=2, status="updated"))
        callback = AsyncMock()
        repository = PersonalDataRepository(self.database, SECRET, "owner", on_profiles_refreshed=callback)
        async with self.database.session() as closing:
            await closing.execute(update(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id == "account-1").values(status="closed"))
            task = asyncio.create_task(repository.apply_refreshed_profiles((PersonalDataProfile("account-1", "복구 금지", now),)))
            await asyncio.sleep(0.05)
            self.assertFalse(task.done())
        self.assertEqual(0, await asyncio.wait_for(task, 5))
        callback.assert_not_awaited()
        async with self.database.session() as session:
            self.assertEqual("closed", (await session.get(PersonalDataAccountORM, "account-1")).status)

    async def test_profile_version_invalidates_existing_sessions_when_erasure_is_staged(self):
        identity = await self.repository.register_identity(self.identity)
        self.assertEqual(1, identity.profile_version)
        self.assertEqual("김영준", (await self.repository.resolve_identity(identity)).display_name)
        action = PersonalDataAction("account-1", "updated")
        await self.repository.stage_actions((action,))
        with self.assertRaises(ValueError):
            await self.repository.resolve_identity(identity)
        await self.repository.finish_actions((action,))
        refreshed = await self.repository.register_identity(replace(self.identity, display_name="변경된 이름"))
        self.assertEqual(2, refreshed.profile_version)
        with self.assertRaises(ValueError):
            await self.repository.resolve_identity(identity)
        self.assertEqual("변경된 이름", (await self.repository.resolve_identity(refreshed)).display_name)

    async def test_closed_account_cannot_be_reactivated_and_erased_profile_name_is_absent(self):
        await self.repository.register_identity(self.identity)
        action = PersonalDataAction("account-1", "closed")
        await self.repository.stage_actions((action,))
        await self.repository.finish_actions((action,))
        with self.assertRaises(ValueError):
            await self.repository.register_identity(self.identity)
        await self.repository.register_accounts((PersonalDataAccount("account-1", datetime.now(timezone.utc)),))
        async with self.database.session() as session:
            row = await session.get(PersonalDataAccountORM, "account-1")
            self.assertIsNone(row.display_name)
            self.assertEqual("closed", row.status)
        self.assertEqual((), await self.repository.due_accounts(datetime.now(timezone.utc), 90))

    async def test_updated_login_preserves_report_cycle_instead_of_reporting_too_early(self):
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=15)
        await self.repository.register_identity(self.identity)
        action = PersonalDataAction("account-1", "updated")
        await self.repository.record_result(("account-1",), (action,), now, deadline)
        await self.repository.finish_actions((action,))
        await self.repository.register_identity(replace(self.identity, display_name="현재 이름"))
        self.assertEqual((), await self.repository.due_accounts(now + timedelta(days=14), 90))
        self.assertEqual(1, len(await self.repository.due_accounts(deadline, 90)))

    async def test_oldest_snapshot_time_and_cycle_deadline_survive_repository_recreation(self):
        now = datetime.now(timezone.utc)
        oldest = now - timedelta(days=90)
        await self.repository.register_accounts((PersonalDataAccount("account-1", oldest),))
        await self.repository.register_identity(self.identity)
        await self.repository.register_accounts((PersonalDataAccount("account-1", now),))
        due = await self.repository.due_accounts(now + timedelta(minutes=1), 90)
        self.assertEqual(oldest, due[0].updated_at)
        await self.repository.mark_reported(("account-1",), now, now + timedelta(days=15))
        recreated = PersonalDataRepository(self.database, SECRET, "owner")
        self.assertEqual((), await recreated.due_accounts(now + timedelta(days=14), 90))
        self.assertEqual(1, len(await recreated.due_accounts(now + timedelta(days=15), 90)))

    async def test_large_account_census_batches_upserts_and_preserves_duplicate_minimum(self):
        now = datetime.now(timezone.utc)
        accounts = tuple(PersonalDataAccount(f"batch-{index}", now) for index in range(1001))
        accounts += (PersonalDataAccount("batch-0", now - timedelta(days=30)), PersonalDataAccount("batch-1000", now - timedelta(days=60)))
        statements = []

        def observe(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO personal_data_accounts"):
                statements.append(statement)

        event.listen(self.database._engine.sync_engine, "before_cursor_execute", observe)
        try:
            await self.repository.register_accounts(accounts)
        finally:
            event.remove(self.database._engine.sync_engine, "before_cursor_execute", observe)
        self.assertEqual(3, len(statements))
        async with self.database.session() as session:
            rows = (await session.execute(select(PersonalDataAccountORM))).scalars().all()
        self.assertEqual(1001, len(rows))
        expected = {account.account_id: account.updated_at for account in accounts}
        self.assertEqual(expected, {row.account_id: row.oldest_retrieved_at for row in rows})
        self.assertTrue(all(row.status == "active" and row.profile_version == 1 for row in rows))

    async def test_batched_census_preserves_restricted_states_profiles_and_reporting_deadline(self):
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=10)
        states = ("active", "updated", "pending_updated", "closed", "pending_closed")
        async with self.database.session() as session:
            for state in states:
                session.add(PersonalDataAccountORM(account_id=f"state-{state}", status=state, display_name="original" if state == "active" else None,
                    email_address="original@example.com" if state == "active" else None, oldest_retrieved_at=now, profile_version=7,
                    last_reported_at=now, next_report_at=deadline))
        accounts = tuple(PersonalDataAccount(f"state-{state}", now - timedelta(days=20)) for state in states)
        await self.repository.register_accounts(accounts + tuple(reversed(accounts)))
        async with self.database.session() as session:
            rows = (await session.execute(select(PersonalDataAccountORM))).scalars().all()
        for row in rows:
            self.assertEqual(row.account_id, f"state-{row.status}")
            self.assertEqual(now - timedelta(days=20) if row.status == "active" else now, row.oldest_retrieved_at)
            self.assertEqual(7, row.profile_version)
            self.assertEqual(deadline, row.next_report_at)
            self.assertEqual(now, row.last_reported_at)
            self.assertEqual("original" if row.status == "active" else None, row.display_name)
            self.assertEqual("original@example.com" if row.status == "active" else None, row.email_address)

    async def test_later_account_batch_failure_rolls_back_earlier_batches(self):
        now = datetime.now(timezone.utc)
        accounts = tuple(PersonalDataAccount(f"batch-{index}", now) for index in range(501))
        calls = 0

        def fail_second_batch(connection, cursor, statement, parameters, context, executemany):
            nonlocal calls
            if statement.startswith("INSERT INTO personal_data_accounts"):
                calls += 1
                if calls == 2:
                    raise RuntimeError("simulated batch failure")

        event.listen(self.database._engine.sync_engine, "before_cursor_execute", fail_second_batch)
        try:
            with self.assertRaisesRegex(RuntimeError, "simulated batch failure"):
                await self.repository.register_accounts(accounts)
        finally:
            event.remove(self.database._engine.sync_engine, "before_cursor_execute", fail_second_batch)
        async with self.database.session() as session:
            self.assertEqual([], (await session.execute(select(PersonalDataAccountORM))).scalars().all())

    async def test_owner_refresh_is_encrypted_and_rotated_durably(self):
        with self.assertRaises(ValueError):
            await self.repository.save_reporting_grant("different-owner", "private-refresh")
        await self.repository.save_reporting_grant("owner", "private-refresh")
        async with self.database.session() as session:
            stored = await session.scalar(select(PersonalDataGrantORM.refresh_token_encrypted))
            self.assertNotIn("private-refresh", stored)
        self.assertEqual(("owner", "private-refresh"), await self.repository.get_reporting_grant())
        await self.repository.save_reporting_grant("owner", "rotated-private-refresh")
        recreated = PersonalDataRepository(self.database, SECRET, "owner")
        self.assertEqual(("owner", "rotated-private-refresh"), await recreated.get_reporting_grant())
        with self.assertRaises(PersonalDataReportingFailure):
            await PersonalDataRepository(self.database, "different-server-key-with-more-than-32-bytes", "owner").get_reporting_grant()

    async def test_rate_limit_deadline_survives_restart_and_status_has_no_secret(self):
        now = datetime.now(timezone.utc)
        retry = now + timedelta(hours=1)
        await self.repository.save_reporting_grant("owner", "private-refresh")
        await self.repository.record_attempt(now, error="reporting_rate_limited", next_attempt_at=retry)
        status = await PersonalDataRepository(self.database, SECRET, "owner").status()
        self.assertEqual(retry.isoformat(), status["next_attempt_at"])
        self.assertEqual("reporting_rate_limited", status["last_error"])
        self.assertNotIn("private-refresh", str(status))

    async def test_closed_owner_response_removes_reporting_credential(self):
        now = datetime.now(timezone.utc)
        await self.repository.save_reporting_grant("owner", "private-refresh")
        due = await self.repository.due_accounts(now + timedelta(minutes=1), 90)
        self.assertEqual(["owner"], [item.account_id for item in due])
        await self.repository.record_result(("owner",), (PersonalDataAction("owner", "closed"),), now, now + timedelta(days=7))
        with self.assertRaises(PersonalDataReportingFailure):
            await self.repository.get_reporting_grant()
        self.assertFalse((await self.repository.status())["owner_authorized"])
