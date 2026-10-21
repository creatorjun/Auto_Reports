# backend/tests/test_sla_status_snapshot_repository.py
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

from src.application.services.snapshot_personal_data import REDACTED_PERSON
from src.domain.entities.sla_status import SlaStatusMetric, SlaStatusSnapshot, SlaStatusTicket
from src.domain.entities.sla_violation_report import SlaStatusDuration
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore
from src.infrastructure.persistence.sla_status_snapshot_repository import SlaStatusSnapshotORM, SlaStatusSnapshotRepository

NOW = datetime(2026, 10, 21, 6, tzinfo=timezone.utc)
DATABASE_URL = os.environ.get("PERSONAL_DATA_TEST_DATABASE_URL")


def snapshot(generated_at=NOW, summary="저장된 SLA 현황"):
    return SlaStatusSnapshot(generated_at, 30, 1, 1, (SlaStatusTicket(
        key="TACEA-1", summary=summary, status="검토 중", assignee="담당자",
        slas=(SlaStatusMetric("resolution", "해결", 100_000, 20_000, 20, False),),
        created_at=NOW - timedelta(days=1), elapsed_days=1, partners=("파트너",),
        reporter="보고자", tac_assignee="TAC 담당자",
        status_durations=(SlaStatusDuration("검토 중", 2.5),),
        warnings=("확인 필요한 이력",), status_duration_calendar="평일 9~18",
        reporter_account_id="sla-cache-reporter", assignee_account_id="sla-cache-assignee",
        tac_assignee_account_id="sla-cache-tac", personal_data_retrieved_at=(NOW - timedelta(days=1)).isoformat(),
        personal_data_field_retrieved_at={"assignee": (NOW - timedelta(hours=1)).isoformat()},
    ),))


class SlaStatusSnapshotRepositoryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        PersonalDataAccountORM.__table__.create(self.engine)
        SlaStatusSnapshotORM.__table__.create(self.engine)

        @asynccontextmanager
        async def session_scope():
            with Session(self.engine, expire_on_commit=False) as session:
                bridge = SimpleNamespace(
                    get_bind=session.get_bind, execute=AsyncMock(side_effect=session.execute),
                    flush=AsyncMock(side_effect=session.flush),
                )
                try:
                    yield bridge
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        self.database = SimpleNamespace(session=session_scope)
        self.repository = SlaStatusSnapshotRepository(self.database)

    def tearDown(self):
        self.engine.dispose()

    def account(self, account_id, status="closed", display_name=None):
        with Session(self.engine) as session:
            session.add(PersonalDataAccountORM(
                account_id=account_id, oldest_retrieved_at=NOW - timedelta(days=1), profile_version=2,
                status=status, display_name=display_name, profile_retrieved_at=NOW,
            ))
            session.commit()

    async def test_recreated_repository_preserves_detail_and_individual_personal_metadata(self):
        original = snapshot()
        self.assertIsNone(await self.repository.load("TACEA"))
        await self.repository.save("TACEA", original)
        restored = await SlaStatusSnapshotRepository(self.database).load("TACEA")
        self.assertEqual(original, restored)
        restored.tickets[0].personal_data_field_retrieved_at["assignee"] = "caller mutation"
        self.assertEqual(original, await self.repository.load("TACEA"))
        self.assertIsNone(await self.repository.load("OTHER"))

    async def test_empty_snapshot_is_stored_without_transient_refresh_metadata(self):
        original = replace(snapshot(), tickets=(), ticket_count=0, sla_count=0)
        saved = await self.repository.save("TACEA", replace(original, refresh_in_progress=True, stale=True, refresh_error="temporary"))
        self.assertEqual(original, saved)
        self.assertEqual(original, await self.repository.load("TACEA"))

    async def test_older_or_equal_result_cannot_overwrite_latest_success(self):
        newest = snapshot(NOW + timedelta(minutes=5), "최신 현황")
        await self.repository.save("TACEA", newest)
        self.assertEqual(newest, await self.repository.save("TACEA", snapshot()))
        self.assertEqual(newest, await self.repository.save("TACEA", snapshot(newest.generated_at, "다른 수집")))
        with Session(self.engine) as session:
            self.assertEqual(1, len(session.execute(select(SlaStatusSnapshotORM)).scalars().all()))

    async def test_save_suppresses_closed_people_and_preserves_input_values(self):
        self.account("sla-cache-assignee")
        self.account("sla-cache-tac", "pending_closed")
        original = snapshot()
        saved = await self.repository.save("TACEA", original)
        self.assertEqual(REDACTED_PERSON, saved.tickets[0].assignee)
        self.assertEqual(REDACTED_PERSON, saved.tickets[0].tac_assignee)
        self.assertEqual("보고자", saved.tickets[0].reporter)
        self.assertEqual("담당자", original.tickets[0].assignee)
        self.assertEqual(saved, await self.repository.load("TACEA"))

    async def test_load_and_rejected_stale_save_apply_current_profile_and_keep_field_times_independent(self):
        newest = snapshot(NOW + timedelta(minutes=5), "최신 현황")
        await self.repository.save("TACEA", newest)
        self.account("sla-cache-reporter", "active", "현재 보고자")
        self.account("sla-cache-assignee")
        saved = await self.repository.save("TACEA", snapshot())
        self.assertEqual("현재 보고자", saved.tickets[0].reporter)
        self.assertEqual(REDACTED_PERSON, saved.tickets[0].assignee)
        self.assertEqual(NOW.isoformat(), saved.tickets[0].personal_data_field_retrieved_at["reporter"])
        self.assertEqual(newest.tickets[0].personal_data_retrieved_at, saved.tickets[0].personal_data_retrieved_at)
        self.assertEqual(newest.generated_at, saved.generated_at)
        self.assertEqual(saved, await self.repository.load("TACEA"))


@unittest.skipUnless(DATABASE_URL, "Requires an isolated PostgreSQL PERSONAL_DATA_TEST_DATABASE_URL")
class SlaStatusSnapshotPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = Database(DATABASE_URL)
        self.repository = SlaStatusSnapshotRepository(self.database)
        await self.cleanup_rows()

    async def cleanup_rows(self):
        async with self.database.session() as session:
            await session.execute(delete(SlaStatusSnapshotORM).where(SlaStatusSnapshotORM.project_key == "SLA_CACHE_TEST"))
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id.in_(
                ("sla-cache-reporter", "sla-cache-assignee", "sla-cache-tac"),
            )))

    async def asyncTearDown(self):
        await self.cleanup_rows()
        await self.database.aclose()

    async def test_concurrent_writers_restore_newest_single_result_after_recreation(self):
        snapshots = [snapshot(NOW + timedelta(seconds=index), f"현황 {index}") for index in range(8)]
        await asyncio.gather(*(self.repository.save("SLA_CACHE_TEST", item) for item in reversed(snapshots)))
        restored = await SlaStatusSnapshotRepository(self.database).load("SLA_CACHE_TEST")
        self.assertEqual(snapshots[-1], restored)
        async with self.database.session() as session:
            rows = (await session.execute(select(SlaStatusSnapshotORM).where(SlaStatusSnapshotORM.project_key == "SLA_CACHE_TEST"))).scalars().all()
            self.assertEqual(1, len(rows))

    async def test_snapshot_participates_in_privacy_collection_and_erasure(self):
        await self.repository.save("SLA_CACHE_TEST", snapshot())
        async with self.database.session() as session:
            store = PersonalDataSnapshotStore(session)
            accounts = {account.account_id: account.updated_at for account in await store.collect_accounts()}
            self.assertEqual(NOW - timedelta(days=1), accounts["sla-cache-reporter"])
            self.assertEqual(NOW - timedelta(hours=1), accounts["sla-cache-assignee"])
            self.assertEqual(1, await store.erase_personal_data(("sla-cache-reporter",)))
        restored = await self.repository.load("SLA_CACHE_TEST")
        self.assertEqual(REDACTED_PERSON, restored.tickets[0].reporter)
        self.assertEqual("담당자", restored.tickets[0].assignee)

    async def test_load_and_save_wait_for_privacy_transaction_and_cannot_reintroduce_closed_name(self):
        await self.repository.save("SLA_CACHE_TEST", snapshot())
        async with self.database.session() as session:
            await PersonalDataSnapshotStore(session).erase_personal_data(("sla-cache-reporter",))
            session.add(PersonalDataAccountORM(account_id="sla-cache-reporter", oldest_retrieved_at=NOW, profile_version=2, status="closed"))
            await session.flush()
            load = asyncio.create_task(self.repository.load("SLA_CACHE_TEST"))
            save = asyncio.create_task(self.repository.save("SLA_CACHE_TEST", snapshot(NOW + timedelta(minutes=1))))
            await asyncio.sleep(0.05)
            self.assertFalse(load.done())
            self.assertFalse(save.done())
        loaded, saved = await asyncio.wait_for(asyncio.gather(load, save), 5)
        self.assertEqual(REDACTED_PERSON, loaded.tickets[0].reporter)
        self.assertEqual(REDACTED_PERSON, saved.tickets[0].reporter)
