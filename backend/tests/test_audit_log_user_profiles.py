# backend/tests/test_audit_log_user_profiles.py
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import create_engine, insert, update
from sqlalchemy.exc import OperationalError

from src.application.ports.audit_log_reader_port import AuditLogReadError
from src.domain.entities.audit_log import AuditLogUserProfile
from src.infrastructure.persistence.audit_log_user_profiles import SqlAuditLogUserProfiles
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM


class AuditLogUserProfilesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        PersonalDataAccountORM.__table__.create(self.engine)
        self.connection = self.engine.connect()
        self.execute = AsyncMock(side_effect=self.connection.execute)
        self.closed_sessions = 0

        @asynccontextmanager
        async def session():
            try:
                yield SimpleNamespace(execute=self.execute)
            finally:
                self.closed_sessions += 1

        self.profiles = SqlAuditLogUserProfiles(SimpleNamespace(session=session))

    def tearDown(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def add(self, account_id: str, status: str = "active", name: str | None = "홍길동", email: str | None = "hong@example.com") -> None:
        self.connection.execute(insert(PersonalDataAccountORM).values(
            account_id=account_id, display_name=name, email_address=email,
            oldest_retrieved_at=datetime.now(timezone.utc), status=status,
        ))

    async def test_only_current_active_profiles_are_read_in_one_query(self) -> None:
        self.add("active")
        self.add("empty", name="  ", email="  ")
        self.add("email-only", name=None, email=" email@example.com ")
        self.add("name-only", name=" 이름 ", email=None)
        for status in ("updated", "closed", "pending_updated", "pending_closed"):
            self.add(status, status)
        profiles = await self.profiles.read_profiles()
        self.assertEqual({
            "active": AuditLogUserProfile("홍길동", "hong@example.com"),
            "empty": AuditLogUserProfile(),
            "email-only": AuditLogUserProfile(email_address="email@example.com"),
            "name-only": AuditLogUserProfile(display_name="이름"),
        }, profiles)
        self.execute.assert_awaited_once()
        self.assertEqual(1, self.closed_sessions)

    async def test_next_request_uses_profile_updates_and_suppression(self) -> None:
        self.add("account")
        self.assertEqual("홍길동", (await self.profiles.read_profiles())["account"].display_name)
        self.connection.execute(update(PersonalDataAccountORM).values(display_name="변경 이름", email_address=None))
        self.assertEqual(AuditLogUserProfile("변경 이름"), (await self.profiles.read_profiles())["account"])
        self.connection.execute(update(PersonalDataAccountORM).values(status="pending_closed"))
        self.assertEqual({}, await self.profiles.read_profiles())

    async def test_database_failures_release_session_and_hide_connection_details(self) -> None:
        for failure in (OperationalError("secret query", {}, Exception("private connection")), OSError("private location")):
            with self.subTest(failure=type(failure).__name__):
                self.execute.side_effect = failure
                with self.assertRaises(AuditLogReadError) as raised:
                    await self.profiles.read_profiles()
                self.assertNotIn("private", str(raised.exception))
                self.assertNotIn("secret", str(raised.exception))
        self.assertEqual(2, self.closed_sessions)
