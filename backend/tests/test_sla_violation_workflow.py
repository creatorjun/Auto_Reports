# backend/tests/test_sla_violation_workflow.py
import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.application.errors import EntityNotFoundError
from src.application.ports.sla_violation_port import SlaViolationRepository, SlaViolationSourcePort
from src.application.use_cases.sla_violation_report import (
    SlaViolationGenerationInProgressError,
    SlaViolationReportUseCase,
    SlaViolationSourceError,
)
from src.domain.entities.sla_violation_report import (
    SlaStatusDuration,
    SlaViolationBreach,
    SlaViolationCycle,
    SlaViolationIssue,
    SlaViolationReport,
    SlaViolationTicket,
)
from src.infrastructure.persistence.sla_violation_repository_impl import SlaViolationRepositoryImpl
from src.infrastructure.persistence.sla_violation_models import SlaViolationReportORM


KST = timezone(timedelta(hours=9))
GENERATED_AT = datetime(2026, 10, 14, 12, tzinfo=KST)


def sample_report() -> SlaViolationReport:
    return SlaViolationReport(
        id=0,
        period="month",
        selected_date=date(2026, 10, 14),
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        generated_at=GENERATED_AT,
        generated_by="tester",
        ticket_count=1,
        initial_response_count=1,
        resolution_count=1,
        tickets=(SlaViolationTicket(
            key="TACEA-1234",
            summary="[서울교통공사] 개선",
            created_at=datetime(2026, 10, 1, tzinfo=KST),
            elapsed_days=13,
            customer="서울교통공사",
            partners=(),
            reporter="보고자",
            assignee="담당자",
            tac_assignee="TAC 담당자",
            current_status="결과 대기 중",
            status_durations=(SlaStatusDuration("할 일", 24.5), SlaStatusDuration("결과 대기 중", 10)),
            breaches=(
                SlaViolationBreach("initial_response", datetime(2026, 10, 2, tzinfo=KST), "할 일"),
                SlaViolationBreach("resolution", None, None),
            ),
            warnings=("위반 시각 확인 불가",),
            issue_type="서비스 요청",
        ),),
        warnings=("일부 위반 시각 확인 불가",),
    )


class SlaViolationUseCaseTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.source = AsyncMock(spec=SlaViolationSourcePort)
        self.source.fetch_issues.return_value = ()
        self.repository = AsyncMock(spec=SlaViolationRepository)
        self.repository.save.side_effect = lambda report: replace(report, id=7)
        self.lock = asyncio.Lock()
        self.use_case = SlaViolationReportUseCase(self.source, self.repository, self.lock, clock=lambda: GENERATED_AT)

    async def test_generation_uses_creation_window_and_saves_empty_snapshot(self) -> None:
        report = await self.use_case.generate("week", date(2026, 10, 14), "tester")
        self.source.fetch_issues.assert_awaited_once_with(
            datetime(2026, 10, 12, tzinfo=KST), datetime(2026, 10, 19, tzinfo=KST),
        )
        self.assertEqual((7, "tester", 0), (report.id, report.generated_by, report.ticket_count))
        self.assertEqual((date(2026, 10, 12), date(2026, 10, 18)), (report.start_date, report.end_date))
        self.assertEqual(report.end_date, self.repository.save.await_args.args[0].end_date)
        self.repository.save.assert_awaited_once()
        self.assertFalse(self.lock.locked())

    async def test_snapshot_time_is_captured_after_fetch(self) -> None:
        finished = GENERATED_AT + timedelta(hours=2)
        clock = Mock(side_effect=[GENERATED_AT, finished])
        self.source.fetch_issues.return_value = (SlaViolationIssue(
            key="TACEA-1", summary="이슈", created_at=GENERATED_AT - timedelta(days=1),
            current_status="할 일", customer=None, partners=None, reporter=None, assignee=None,
            tac_assignee=None, cycles=(SlaViolationCycle("resolution", GENERATED_AT),),
        ),)
        use_case = SlaViolationReportUseCase(self.source, self.repository, self.lock, clock=clock)
        report = await use_case.generate("month", date(2026, 10, 14), "tester")
        self.assertEqual(finished, report.generated_at)
        self.assertEqual(1, report.tickets[0].elapsed_days)
        self.assertIsNone(report.tickets[0].status_durations)
        self.assertEqual("resolution_sla", report.tickets[0].status_durations_basis)

    async def test_upstream_failure_never_saves_or_leaves_lock_held(self) -> None:
        self.source.fetch_issues.side_effect = RuntimeError("private Jira failure")
        with self.assertRaises(SlaViolationSourceError):
            await self.use_case.generate("month", date(2026, 10, 14), "tester")
        self.repository.save.assert_not_awaited()
        self.assertFalse(self.lock.locked())

    async def test_cancellation_never_saves_and_releases_shared_lock(self) -> None:
        self.source.fetch_issues.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.use_case.generate("month", date(2026, 10, 14), "tester")
        self.repository.save.assert_not_awaited()
        self.assertFalse(self.lock.locked())

    async def test_future_selection_does_not_fetch_or_save(self) -> None:
        with self.assertRaises(ValueError):
            await self.use_case.generate("year", date(2026, 10, 15), "tester")
        self.source.fetch_issues.assert_not_awaited()
        self.repository.save.assert_not_awaited()

    async def test_concurrent_generation_fails_without_second_fetch(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def fetch(start, end):
            started.set()
            await release.wait()
            return ()

        self.source.fetch_issues.side_effect = fetch
        first = asyncio.create_task(self.use_case.generate("year", date(2026, 10, 14), "tester"))
        try:
            await asyncio.wait_for(started.wait(), 1)
            second = SlaViolationReportUseCase(self.source, self.repository, self.lock, clock=lambda: GENERATED_AT)
            with self.assertRaises(SlaViolationGenerationInProgressError):
                await second.generate("week", date(2026, 10, 14), "tester")
        finally:
            release.set()
            await first
        self.source.fetch_issues.assert_awaited_once()
        self.repository.save.assert_awaited_once()

    async def test_persistence_failure_is_not_misclassified_as_jira_failure(self) -> None:
        self.repository.save.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await self.use_case.generate("month", date(2026, 10, 14), "tester")
        self.assertFalse(self.lock.locked())

    async def test_reads_return_stored_snapshot_without_refresh(self) -> None:
        stored = replace(sample_report(), id=3, period="week", selected_date=date(2026, 10, 7), start_date=date(2026, 10, 5), end_date=date(2026, 10, 7))
        self.repository.get_latest.return_value = stored
        self.repository.get_by_id.return_value = stored
        self.assertIs(stored, await self.use_case.get_latest())
        self.assertIs(stored, await self.use_case.get_by_id(3))
        self.source.fetch_issues.assert_not_awaited()
        self.repository.get_by_id.return_value = None
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.get_by_id(9)


class SlaViolationRepositoryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.rows = []
        self.session = SimpleNamespace(
            add=lambda row: self.rows.append(row), flush=AsyncMock(), commit=AsyncMock(),
            rollback=AsyncMock(), execute=AsyncMock(),
        )

        async def assign_id():
            self.rows[-1].id = len(self.rows)

        self.session.flush.side_effect = assign_id
        self.repository = SlaViolationRepositoryImpl(self.session)

    async def test_commit_and_round_trip_preserve_snapshot_and_unknown_values(self) -> None:
        report = sample_report()
        saved = await self.repository.save(report)
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()
        self.assertEqual(1, saved.id)
        self.assertEqual(saved, self.repository._to_report(self.rows[-1]))
        ticket = replace(report.tickets[0], partners=None, status_durations=None, issue_type=None)
        unknown = await self.repository.save(replace(report, tickets=(ticket,)))
        self.assertEqual(unknown, self.repository._to_report(self.rows[-1]))

    async def test_old_snapshot_reads_unknown_issue_type_without_changing_stored_payload(self) -> None:
        saved = await self.repository.save(sample_report())
        row = self.rows[-1]
        row.payload["tickets"][0].pop("issue_type")
        original_payload = deepcopy(row.payload)
        self.session.commit.reset_mock()
        self.session.execute.return_value = Mock(scalar_one_or_none=lambda: row)
        expected = replace(saved, tickets=(replace(saved.tickets[0], issue_type=None),))
        self.assertEqual(expected, await self.repository.get_latest())
        self.assertEqual(expected, await self.repository.get_by_id(saved.id))
        self.assertEqual(original_payload, row.payload)
        self.session.commit.assert_not_awaited()

    async def test_resolution_sla_basis_and_calendar_round_trip_without_recomputing_hours(self) -> None:
        report = sample_report()
        ticket = replace(
            report.tickets[0], status_durations=(SlaStatusDuration("할 일", 0.5000001), SlaStatusDuration("이슈 리뷰 중", 11.25)),
            status_durations_basis="resolution_sla", status_duration_calendar="계약 업무시간",
        )
        saved = await self.repository.save(replace(report, tickets=(ticket,)))
        row = self.rows[-1]
        self.assertEqual(saved, self.repository._to_report(row))
        stored = row.payload["tickets"][0]
        self.assertEqual("resolution_sla", stored["status_durations_basis"])
        self.assertEqual("계약 업무시간", stored["status_duration_calendar"])
        self.assertEqual(0.5000001, stored["status_durations"][0]["hours"])

    async def test_legacy_status_hours_keep_wall_clock_basis_without_mutating_history(self) -> None:
        saved = await self.repository.save(sample_report())
        row = self.rows[-1]
        for field in ("status_durations_basis", "status_duration_calendar"):
            row.payload["tickets"][0].pop(field)
        original_payload = deepcopy(row.payload)
        self.session.commit.reset_mock()
        self.session.execute.return_value = Mock(scalar_one_or_none=lambda: row)
        for stored in (await self.repository.get_latest(), await self.repository.get_by_id(saved.id)):
            ticket = stored.tickets[0]
            self.assertEqual("wall_clock", ticket.status_durations_basis)
            self.assertIsNone(ticket.status_duration_calendar)
            self.assertEqual(saved.tickets[0].status_durations, ticket.status_durations)
        self.assertEqual(original_payload, row.payload)
        self.session.commit.assert_not_awaited()

    async def test_cycle_timings_round_trip_as_json_without_combining_reset_cycles(self) -> None:
        report = sample_report()
        cycles = (
            SlaViolationCycle("initial_response", None, breached=False, goal_ms=14400000, elapsed_ms=3600000, exceeded_ms=0, started_at=GENERATED_AT - timedelta(days=1), stopped_at=GENERATED_AT),
            SlaViolationCycle("resolution", GENERATED_AT, goal_ms=144000000, elapsed_ms=151200000, exceeded_ms=7200000, status="할 일"),
            SlaViolationCycle("resolution", None, ongoing=True, paused=True, goal_ms=432000000, elapsed_ms=None, exceeded_ms=None),
        )
        saved = await self.repository.save(replace(report, tickets=(replace(report.tickets[0], sla_cycles=cycles),)))
        row = self.rows[-1]
        self.assertEqual(saved, self.repository._to_report(row))
        stored = row.payload["tickets"][0]["sla_cycles"]
        self.assertEqual([0, 7200000, None], [cycle["exceeded_ms"] for cycle in stored])
        self.assertEqual(GENERATED_AT.isoformat(), stored[0]["stopped_at"])
        self.assertEqual(GENERATED_AT.isoformat(), stored[1]["breached_at"])
        self.assertTrue(stored[2]["paused"])

    async def test_legacy_snapshot_has_unknown_cycle_timings_without_mutation_or_refresh(self) -> None:
        saved = await self.repository.save(sample_report())
        row = self.rows[-1]
        row.payload["tickets"][0].pop("sla_cycles")
        original_payload = deepcopy(row.payload)
        self.session.commit.reset_mock()
        self.session.execute.return_value = Mock(scalar_one_or_none=lambda: row)
        for stored in (await self.repository.get_latest(), await self.repository.get_by_id(saved.id)):
            self.assertIsNone(stored.tickets[0].sla_cycles)
            self.assertEqual(saved.tickets[0].breaches, stored.tickets[0].breaches)
        self.assertEqual(original_payload, row.payload)
        self.session.commit.assert_not_awaited()

    async def test_failed_commit_rolls_back_and_raises(self) -> None:
        self.session.commit.side_effect = RuntimeError("write failed")
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await self.repository.save(sample_report())
        self.session.rollback.assert_awaited_once()

    async def test_cancelled_flush_rolls_back_without_commit(self) -> None:
        self.session.flush.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.repository.save(sample_report())
        self.session.rollback.assert_awaited_once()
        self.session.commit.assert_not_awaited()

    async def test_latest_and_history_sort_by_generation_then_id_and_omit_payload(self) -> None:
        saved = await self.repository.save(sample_report())
        row = self.rows[-1]
        self.session.execute.return_value = Mock(scalar_one_or_none=lambda: row, all=lambda: [row])
        self.assertEqual(saved, await self.repository.get_latest())
        sql = str(self.session.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("ORDER BY sla_violation_reports.generated_at DESC, sla_violation_reports.id DESC", sql)
        self.assertIn("LIMIT 1", sql)
        summaries = await self.repository.list_summaries(7, 3)
        sql = str(self.session.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertNotIn("payload", sql)
        self.assertIn("LIMIT 7 OFFSET 3", sql)
        self.assertEqual((saved.id, 1, 1), (summaries[0].id, summaries[0].initial_response_count, summaries[0].resolution_count))
        self.assertNotIn("tickets", asdict(summaries[0]))


class SqliteSessionBridge:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, row: object) -> None:
        self.session.add(row)

    async def flush(self) -> None:
        self.session.flush()

    async def commit(self) -> None:
        self.session.commit()

    async def rollback(self) -> None:
        self.session.rollback()

    async def execute(self, statement):
        return self.session.execute(statement)


class SlaViolationSqliteIntegrationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        SlaViolationReportORM.__table__.create(self.engine)

    async def test_committed_snapshot_survives_new_session_and_orders_history(self) -> None:
        with Session(self.engine, expire_on_commit=False) as session:
            repository = SlaViolationRepositoryImpl(SqliteSessionBridge(session))
            first = await repository.save(sample_report())
            second = await repository.save(replace(sample_report(), generated_by="second"))
            older = await repository.save(replace(sample_report(), generated_at=GENERATED_AT - timedelta(days=1)))
        with Session(self.engine) as session:
            repository = SlaViolationRepositoryImpl(SqliteSessionBridge(session))
            self.assertEqual(second, await repository.get_latest())
            self.assertEqual(first, await repository.get_by_id(first.id))
            history = await repository.list_summaries(2, 1)
            self.assertEqual([first.id, older.id], [row.id for row in history])
            self.assertIsNone(await repository.get_by_id(999))

    async def test_failed_database_write_rolls_back_and_session_can_save_next_report(self) -> None:
        with Session(self.engine, expire_on_commit=False) as session:
            repository = SlaViolationRepositoryImpl(SqliteSessionBridge(session))
            with self.assertRaises(IntegrityError):
                await repository.save(replace(sample_report(), generated_by=None))
            self.assertIsNone(await repository.get_latest())
            saved = await repository.save(sample_report())
            self.assertEqual(saved, await repository.get_latest())
            self.assertEqual(1, len(await repository.list_summaries(10, 0)))
