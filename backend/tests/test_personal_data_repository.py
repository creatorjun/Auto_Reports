# backend/tests/test_personal_data_repository.py
import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from src.application.ports.personal_data_port import PersonalDataReportingFailure
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM, PersonalDataGrantORM
from src.infrastructure.persistence.personal_data_repository import PersonalDataRepository

DATABASE_URL = os.environ.get("PERSONAL_DATA_TEST_DATABASE_URL")
SECRET = "personal-data-tests-only-server-key-with-32-bytes"


@unittest.skipUnless(DATABASE_URL, "Requires an isolated PostgreSQL PERSONAL_DATA_TEST_DATABASE_URL")
class PersonalDataRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = Database(DATABASE_URL)
        self.repository = PersonalDataRepository(self.database, SECRET, "owner")
        self.identity = AuthIdentity("jira:site:account-1", "김영준", "jira", 9999999999)
        async with self.database.session() as session:
            await session.execute(delete(PersonalDataAccountORM))
            await session.execute(delete(PersonalDataGrantORM))

    async def asyncTearDown(self):
        await self.database.aclose()

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
