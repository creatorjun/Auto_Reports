# backend/tests/test_issue_management_snapshot_repository.py
import asyncio
import os
import unittest
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot
from src.application.services.snapshot_personal_data import REDACTED_PERSON
from src.domain.entities.widget_data import RecentIssueDetail
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.issue_management_snapshot_repository import IssueManagementSnapshotORM, IssueManagementSnapshotRepository
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore

NOW = datetime(2026, 10, 19, 7, tzinfo=timezone.utc)
DATABASE_URL = os.environ.get("PERSONAL_DATA_TEST_DATABASE_URL")


def snapshot(synced_at=NOW, summary="저장된 이슈"):
    return IssueManagementSnapshot((RecentIssueDetail(
        "TACEA-1", summary, "개선", "결과 대기 중", 7,
        "2026-10-01T23:30:00.000+0900", 18,
        reporter="보고자", tac_team="담당자", tac_assignee="TAC 담당자",
        reporter_account_id="cache-reporter", tac_team_account_id="cache-team",
        tac_assignee_account_id="cache-tac", personal_data_retrieved_at=(NOW - timedelta(days=1)).isoformat(),
    ),), synced_at, NOW - timedelta(minutes=30))


class IssueManagementSnapshotRepositoryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        PersonalDataAccountORM.__table__.create(self.engine)
        IssueManagementSnapshotORM.__table__.create(self.engine)

        @asynccontextmanager
        async def session_scope():
            with Session(self.engine, expire_on_commit=False) as session:
                bridge = SimpleNamespace(
                    get_bind=session.get_bind,
                    execute=AsyncMock(side_effect=session.execute),
                    flush=AsyncMock(side_effect=session.flush),
                )
                try:
                    yield bridge
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        self.database = SimpleNamespace(session=session_scope)
        self.repository = IssueManagementSnapshotRepository(self.database)

    def tearDown(self):
        self.engine.dispose()

    def close_account(self, account_id):
        with Session(self.engine) as session:
            session.add(PersonalDataAccountORM(
                account_id=account_id, oldest_retrieved_at=NOW, profile_version=2, status="closed",
            ))
            session.commit()

    async def test_missing_and_empty_snapshots_are_distinct(self):
        self.assertIsNone(await self.repository.load("TACEA"))
        empty = replace(snapshot(), issues=())
        self.assertEqual(empty, await self.repository.save("TACEA", empty))
        self.assertEqual(empty, await IssueManagementSnapshotRepository(self.database).load("TACEA"))
        self.assertIsNone(await self.repository.load("OTHER"))

    async def test_recreated_repository_restores_dates_and_personal_identity_metadata(self):
        original = snapshot()
        await self.repository.save("TACEA", original)
        restored = await IssueManagementSnapshotRepository(self.database).load("TACEA")
        self.assertEqual(original, restored)
        restored.issues[0].summary = "호출자 변경"
        self.assertEqual(original, await self.repository.load("TACEA"))

    async def test_transition_maps_round_trip_and_survive_personal_data_suppression(self):
        original = replace(snapshot(),
            status_transitions={"TACEA-1": {"닫힘": "2026-10-18T23:59:00+09:00"}},
            issue_updated_at={"TACEA-1": "2026-10-19T10:00:00+09:00"},
            transition_history_ready=True,
        )
        await self.repository.save("TACEA", original)
        self.close_account("cache-reporter")
        restored = await IssueManagementSnapshotRepository(self.database).load("TACEA")
        self.assertEqual(REDACTED_PERSON, restored.issues[0].reporter)
        self.assertTrue(restored.transition_history_ready)
        self.assertEqual(original.status_transitions, restored.status_transitions)
        self.assertEqual(original.issue_updated_at, restored.issue_updated_at)
        restored.status_transitions["TACEA-1"]["닫힘"] = "changed"
        restored.issue_updated_at.clear()
        reread = await self.repository.load("TACEA")
        self.assertEqual(original.status_transitions, reread.status_transitions)
        self.assertEqual(original.issue_updated_at, reread.issue_updated_at)

    async def test_legacy_payload_loads_without_transition_fields_or_migration(self):
        await self.repository.save("TACEA", snapshot())
        with Session(self.engine) as session:
            row = session.execute(select(IssueManagementSnapshotORM)).scalar_one()
            row.payload = {"issues": row.payload["issues"]}
            session.commit()
        restored = await self.repository.load("TACEA")
        self.assertFalse(restored.transition_history_ready)
        self.assertEqual({}, restored.status_transitions)
        self.assertEqual({}, restored.issue_updated_at)
        self.assertEqual(snapshot().issues, restored.issues)

    async def test_old_or_equal_timestamp_cannot_replace_newer_snapshot(self):
        newest = snapshot(NOW + timedelta(minutes=5), "최신 이슈")
        await self.repository.save("TACEA", newest)
        self.assertEqual(newest, await self.repository.save("TACEA", snapshot()))
        self.assertEqual(newest, await self.repository.save("TACEA", snapshot(newest.synced_at, "동시 작업")))
        with Session(self.engine) as session:
            self.assertEqual(1, len(session.execute(select(IssueManagementSnapshotORM)).scalars().all()))

    async def test_save_returns_and_persists_suppressed_copy_without_mutating_input(self):
        self.close_account("cache-reporter")
        self.close_account("cache-tac")
        original = snapshot()
        saved = await self.repository.save("TACEA", original)
        self.assertEqual(REDACTED_PERSON, saved.issues[0].reporter)
        self.assertEqual(REDACTED_PERSON, saved.issues[0].tac_assignee)
        self.assertEqual("담당자", saved.issues[0].tac_team)
        self.assertEqual("보고자", original.issues[0].reporter)
        self.assertEqual(saved, await self.repository.load("TACEA"))

    async def test_load_suppresses_account_closed_after_snapshot_was_saved(self):
        await self.repository.save("TACEA", snapshot())
        self.close_account("cache-team")
        restored = await self.repository.load("TACEA")
        self.assertEqual(REDACTED_PERSON, restored.issues[0].tac_team)
        with Session(self.engine) as session:
            row = session.execute(select(IssueManagementSnapshotORM)).scalar_one()
            self.assertEqual(REDACTED_PERSON, row.payload["issues"][0]["tac_team"])
            self.assertEqual("cache-team", row.payload["issues"][0]["tac_team_account_id"])

    async def test_rejected_stale_save_also_suppresses_existing_snapshot(self):
        newer = snapshot(NOW + timedelta(minutes=5), "최신 이슈")
        await self.repository.save("TACEA", newer)
        self.close_account("cache-reporter")
        returned = await self.repository.save("TACEA", snapshot())
        self.assertEqual(newer.synced_at, returned.synced_at)
        self.assertEqual("최신 이슈", returned.issues[0].summary)
        self.assertEqual(REDACTED_PERSON, returned.issues[0].reporter)


@unittest.skipUnless(DATABASE_URL, "Requires an isolated PostgreSQL PERSONAL_DATA_TEST_DATABASE_URL")
class IssueManagementSnapshotPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = Database(DATABASE_URL)
        self.repository = IssueManagementSnapshotRepository(self.database)
        async with self.database.session() as session:
            await session.execute(delete(IssueManagementSnapshotORM).where(IssueManagementSnapshotORM.project_key == "CACHE_TEST"))
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id.in_(("cache-reporter", "cache-team", "cache-tac"))))

    async def asyncTearDown(self):
        async with self.database.session() as session:
            await session.execute(delete(IssueManagementSnapshotORM).where(IssueManagementSnapshotORM.project_key == "CACHE_TEST"))
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id.in_(("cache-reporter", "cache-team", "cache-tac"))))
        await self.database.aclose()

    async def test_concurrent_writers_preserve_newest_single_snapshot(self):
        snapshots = [snapshot(NOW + timedelta(seconds=index), f"이슈 {index}") for index in range(8)]
        await asyncio.gather(*(self.repository.save("CACHE_TEST", item) for item in reversed(snapshots)))
        self.assertEqual(snapshots[-1], await self.repository.load("CACHE_TEST"))
        async with self.database.session() as session:
            rows = (await session.execute(select(IssueManagementSnapshotORM).where(IssueManagementSnapshotORM.project_key == "CACHE_TEST"))).scalars().all()
            self.assertEqual(1, len(rows))

    async def test_snapshot_participates_in_account_collection_and_erasure(self):
        await self.repository.save("CACHE_TEST", snapshot())
        async with self.database.session() as session:
            store = PersonalDataSnapshotStore(session)
            accounts = {account.account_id: account.updated_at for account in await store.collect_accounts()}
            self.assertEqual(NOW - timedelta(days=1), accounts["cache-reporter"])
            self.assertEqual(NOW - timedelta(days=1), accounts["cache-team"])
            self.assertEqual(NOW - timedelta(days=1), accounts["cache-tac"])
            self.assertEqual(1, await store.erase_personal_data(("cache-reporter",)))
            self.assertEqual((), store.erased_report_ids)
        restored = await self.repository.load("CACHE_TEST")
        self.assertEqual(REDACTED_PERSON, restored.issues[0].reporter)
        self.assertEqual("담당자", restored.issues[0].tac_team)

    async def test_load_and_save_wait_for_privacy_erasure_transaction(self):
        await self.repository.save("CACHE_TEST", snapshot())
        async with self.database.session() as session:
            await PersonalDataSnapshotStore(session).erase_personal_data(("cache-reporter",))
            session.add(PersonalDataAccountORM(account_id="cache-reporter", oldest_retrieved_at=NOW, profile_version=2, status="closed"))
            await session.flush()
            load = asyncio.create_task(self.repository.load("CACHE_TEST"))
            save = asyncio.create_task(self.repository.save("CACHE_TEST", snapshot(NOW + timedelta(minutes=1))))
            await asyncio.sleep(0.05)
            self.assertFalse(load.done())
            self.assertFalse(save.done())
        loaded, saved = await asyncio.wait_for(asyncio.gather(load, save), 5)
        self.assertEqual(REDACTED_PERSON, loaded.issues[0].reporter)
        self.assertEqual(REDACTED_PERSON, saved.issues[0].reporter)
        self.assertEqual(REDACTED_PERSON, (await self.repository.load("CACHE_TEST")).issues[0].reporter)
