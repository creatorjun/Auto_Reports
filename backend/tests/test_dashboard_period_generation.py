# backend/tests/test_dashboard_period_generation.py
import dataclasses
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy import Column, Date, DateTime, Integer, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.orm import Session

from src.application.ports.report_analyzer_port import ReportAnalyzerPort
from src.application.ports.report_cache_port import ReportCachePort
from src.application.ports.report_repository import ReportRepository
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.services.report_period import report_period_dates
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.widgets.collector_factory import CollectorEntry
from src.domain.constants import KST
from src.domain.entities.report import Report, ReportScope
from src.domain.entities.widget import WidgetResult
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.presentation.api.deps import get_audit, get_job_runner
from src.presentation.api.v1.trigger import router


class ReportPeriodTest(unittest.TestCase):
    def test_calendar_boundaries_include_leap_day_and_cross_year_week(self) -> None:
        for period, selected, expected in (
            ("week", date(2026, 1, 1), (date(2025, 12, 29), date(2026, 1, 4))),
            ("month", date(2024, 2, 13), (date(2024, 2, 1), date(2024, 2, 29))),
            ("year", date(2025, 7, 4), (date(2025, 1, 1), date(2025, 12, 31))),
        ):
            with self.subTest(period=period):
                start, end = report_period_dates(period, selected, date(2026, 10, 14))
                self.assertEqual(expected, (start.date(), end.date()))
                self.assertEqual((0, 0, 0), (start.hour, start.minute, start.second))
                self.assertEqual((23, 59, 59), (end.hour, end.minute, end.second))
                self.assertEqual(timedelta(hours=9), start.utcoffset())
                self.assertEqual(timedelta(hours=9), end.utcoffset())

    def test_current_period_retains_full_calendar_range(self) -> None:
        start, end = report_period_dates("year", date(2026, 10, 14), date(2026, 10, 14))
        self.assertEqual(date(2026, 1, 1), start.date())
        self.assertEqual(date(2026, 12, 31), end.date())

    def test_future_reference_date_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "오늘 이후"):
            report_period_dates("week", date(2026, 10, 15), date(2026, 10, 14))


class DashboardTriggerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.runner = AsyncMock()
        self.audit = Mock()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_job_runner] = lambda: self.runner
        app.dependency_overrides[get_audit] = lambda: self.audit
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_calendar_requests_pass_standard_scope_and_fresh_jira_queries(self) -> None:
        now = datetime(2026, 10, 13, 15, 15, tzinfo=timezone.utc).astimezone(KST)
        for period, expected in (
            ("week", (date(2026, 10, 12), date(2026, 10, 18))),
            ("month", (date(2026, 10, 1), date(2026, 10, 31))),
            ("year", (date(2026, 1, 1), date(2026, 12, 31))),
        ):
            with self.subTest(period=period):
                with patch("src.presentation.api.v1.trigger.datetime", wraps=datetime) as clock:
                    clock.now.return_value = now
                    response = await self.client.post("/api/v1/trigger/", json={"period": period, "date": "2026-10-14"})
                self.assertEqual(202, response.status_code, response.text)
                clock.now.assert_called_once_with(KST)
                args, kwargs = self.runner.submit.await_args
                self.assertEqual(response.json()["job_id"], args[0])
                self.assertEqual(expected, (args[1].date(), args[2].date()))
                self.assertEqual({"bypass_jira_cache": True, "force_standard": True}, kwargs)
                self.assertEqual(expected[0].isoformat(), self.audit.record.call_args.kwargs["start"])
                self.assertEqual(expected[1].isoformat(), self.audit.record.call_args.kwargs["end"])

    async def test_invalid_requests_do_not_start_jobs(self) -> None:
        for body in (
            {"period": "week"},
            {"date": "2026-10-14"},
            {"period": "day", "date": "2026-10-14"},
            {"period": "month", "date": "2026-02-30"},
            {"period": "year", "date": "2025-01-01", "start_date": "2025-01-01"},
            {"period": "year", "date": "2025-01-01", "end_date": "2025-12-31"},
            {"period": "week", "date": "9999-01-01"},
        ):
            with self.subTest(body=body):
                response = await self.client.post("/api/v1/trigger/", json=body)
                self.assertEqual(422, response.status_code, response.text)
        self.runner.submit.assert_not_awaited()
        self.audit.record.assert_not_called()

    async def test_existing_annual_date_range_keeps_legacy_scope_selection(self) -> None:
        response = await self.client.post("/api/v1/trigger/", json={"start_date": "2025-01-01", "end_date": "2025-12-31"})
        self.assertEqual(202, response.status_code, response.text)
        self.runner.submit.assert_awaited_once_with(
            response.json()["job_id"],
            datetime(2025, 1, 1, tzinfo=KST),
            datetime(2025, 12, 31, 23, 59, 59, tzinfo=KST),
            bypass_jira_cache=True,
        )


class DashboardGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.base_widget = WidgetResult("기존 현황", 7)
        self.monthly_widget = WidgetResult("기존 월별 추이", 12)
        self.annual_widget = WidgetResult("연간 보고서 전용", 3)
        self.base_factory = Mock(return_value=[CollectorEntry(
            WidgetId.YEARLY_CREATED, AsyncMock(collect=AsyncMock(return_value=self.base_widget)),
        )])
        self.monthly_factory = Mock(return_value=[(
            [WidgetId.MONTHLY_CREATED], AsyncMock(collect=AsyncMock(return_value=self.monthly_widget)),
        )])
        self.annual_factory = Mock(return_value=[CollectorEntry(
            WidgetId.REDEPLOYMENT_ANALYTICS, AsyncMock(collect=AsyncMock(return_value=self.annual_widget)),
        )])
        self.assembler = ReportAssembler(
            WidgetQueryBuilder(QueryConfig("T", ["개선"], [], ["Closed"], 30, 2026)),
            self.base_factory, self.monthly_factory, self.annual_factory,
        )
        self.repository = AsyncMock(spec=ReportRepository)
        self.repository.save.side_effect = lambda report: Report(**{
            field.name: getattr(report, field.name) for field in dataclasses.fields(report)
        }, id=10)
        self.cache = AsyncMock(spec=ReportCachePort)
        self.analyzer = AsyncMock(spec=ReportAnalyzerPort)
        self.analyzer.analyze.return_value = None
        self.use_case = GenerateReportUseCase(self.assembler, self.analyzer, self.repository, self.cache, retention_weeks=0)
        self.now = datetime(2026, 10, 14, 11, 53, tzinfo=KST)

    async def test_calendar_generations_keep_standard_widgets_and_actual_collection_time(self) -> None:
        for period in ("week", "month", "year"):
            with self.subTest(period=period):
                start, end = report_period_dates(period, date(2026, 1, 10), self.now.date())
                report = await self.use_case.execute(self.now, start, end, force_standard=True)
                self.assertEqual(ReportScope.STANDARD, report.scope)
                self.assertIsNone(report.report_year)
                self.assertEqual({WidgetId.YEARLY_CREATED, WidgetId.MONTHLY_CREATED}, set(report.widgets))
                self.assertIs(self.base_widget, report.widgets[WidgetId.YEARLY_CREATED])
                self.assertIs(self.monthly_widget, report.widgets[WidgetId.MONTHLY_CREATED])
                self.assertEqual((start.date(), end.date()), (report.week_start, report.week_end))
                self.assertEqual(self.now, self.base_factory.call_args.args[1])
                self.cache.set_latest_id.assert_awaited_with(10)
        self.annual_factory.assert_not_called()

    async def test_legacy_annual_generation_keeps_annual_widgets_and_latest_separation(self) -> None:
        report = await self.use_case.execute(
            self.now, datetime(2025, 1, 1, tzinfo=KST), datetime(2025, 12, 31, 23, 59, 59, tzinfo=KST),
        )
        self.assertEqual(ReportScope.ANNUAL, report.scope)
        self.assertEqual(2025, report.report_year)
        self.assertEqual(3, len(report.widgets))
        self.annual_factory.assert_called_once()
        self.cache.set_latest_id.assert_not_awaited()


class ReportRetentionTest(unittest.IsolatedAsyncioTestCase):
    async def test_retention_uses_creation_time_and_preserves_new_historical_reports(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        metadata = MetaData()
        table = Table(
            "reports", metadata,
            Column("id", Integer, primary_key=True),
            Column("scope", String, nullable=False),
            Column("week_start", Date, nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        metadata.create_all(engine)
        with Session(engine) as session:
            session.execute(insert(table), [
                {"id": 1, "scope": "standard", "week_start": date(2024, 1, 1), "created_at": datetime(2026, 10, 14, 11, 53, tzinfo=KST)},
                {"id": 2, "scope": "standard", "week_start": date(2026, 10, 12), "created_at": datetime(2025, 10, 14, 23, 59, 59, tzinfo=KST)},
                {"id": 3, "scope": "standard", "week_start": date(2024, 1, 1), "created_at": datetime(2025, 10, 15, tzinfo=KST)},
                {"id": 4, "scope": "annual", "week_start": date(2024, 1, 1), "created_at": datetime(2024, 12, 31, tzinfo=KST)},
            ])
            session.commit()
            adapter = AsyncMock(execute=AsyncMock(side_effect=session.execute), flush=AsyncMock(side_effect=session.flush))
            repository = ReportRepositoryImpl(adapter)

            self.assertEqual([2], await repository.delete_before(date(2025, 10, 15)))
            self.assertEqual([1, 3, 4], list(session.scalars(select(table.c.id).order_by(table.c.id))))
            self.assertEqual([3], await repository.delete_before(date(2025, 10, 16)))
            self.assertEqual([1, 4], list(session.scalars(select(table.c.id).order_by(table.c.id))))
            self.assertEqual([1], await repository.delete_before(date(2026, 10, 15)))
            self.assertEqual([4], list(session.scalars(select(table.c.id).order_by(table.c.id))))
