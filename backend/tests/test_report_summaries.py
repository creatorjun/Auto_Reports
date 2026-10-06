# backend/tests/test_report_summaries.py
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI
from sqlalchemy.dialects import postgresql

from src.application.ports.report_repository import ReportRepository
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.entities.report import ReportScope
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.presentation.api.deps import get_auth
from src.presentation.api.v1.deps import get_get_use_case
from src.presentation.api.v1.router import router
from src.presentation.mappers.report_mapper import ReportMapper


class ReportSummaryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rows = [SimpleNamespace(
            id=report_id,
            week_start=date(2026, 1, 1),
            week_end=date(2026, 12, 31),
            report_date="2026-10-06",
            created_at=datetime(2026, 10, 6, report_id, tzinfo=timezone.utc),
            ai_analysis={"summary": "요약", "risks": [], "recommendations": [], "sentiment": "warning"} if report_id == 2 else None,
            scope=ReportScope.ANNUAL.value if report_id == 2 else ReportScope.STANDARD.value,
            report_year=2026 if report_id == 2 else None,
            widgets={},
        ) for report_id in (2, 1)]
        self.session = SimpleNamespace(execute=AsyncMock(return_value=Mock(all=lambda: self.rows)))
        self.repository = ReportRepositoryImpl(self.session)
        self.use_case = GetReportUseCase(self.repository, AsyncMock())

    async def test_summary_query_omits_widgets_and_preserves_order_and_pagination(self):
        with patch("src.infrastructure.persistence.report_repository_impl.deserialize_widget", side_effect=AssertionError("Widget detail loaded")):
            summaries = await self.use_case.get_summaries(limit=7, offset=3)
        statement = self.session.execute.call_args.args[0]
        sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertNotIn("reports.widgets", sql)
        self.assertIn("ORDER BY reports.created_at DESC", sql)
        self.assertIn("LIMIT 7 OFFSET 3", sql)
        self.assertEqual([2, 1], [summary.id for summary in summaries])
        expected = [ReportMapper.to_summary(self.repository._to_entity(row)) for row in self.rows]
        self.assertEqual(expected, [ReportMapper.to_summary(summary) for summary in summaries])
        self.assertEqual(9 * 3600, summaries[0].created_at.utcoffset().total_seconds())

    async def test_legacy_repository_summary_fallback_preserves_full_reports(self):
        reports = [self.repository._to_entity(row) for row in self.rows]
        repository = SimpleNamespace(find_all=AsyncMock(return_value=reports))
        summaries = await ReportRepository.find_summaries(repository, limit=7, offset=3)
        repository.find_all.assert_awaited_once_with(limit=7, offset=3)
        self.assertEqual(
            [ReportMapper.to_summary(report) for report in reports],
            [ReportMapper.to_summary(summary) for summary in summaries],
        )

    async def test_history_api_keeps_response_fields_and_authentication(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_get_use_case] = lambda: self.use_case
        app.dependency_overrides[get_auth] = lambda: SimpleNamespace(enabled=True, decode_access_token=lambda token: "tester")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            unauthenticated = await client.get("/api/v1/reports/")
            self.assertEqual(401, unauthenticated.status_code)
            self.session.execute.assert_not_awaited()
            response = await client.get("/api/v1/reports/?limit=7&offset=3", headers={"Authorization": "Bearer test"})
        self.assertEqual(200, response.status_code)
        expected = [ReportMapper.to_summary(self.repository._to_entity(row)).model_dump(mode="json") for row in self.rows]
        self.assertEqual(expected, response.json())

    async def test_empty_history_returns_empty_list(self):
        self.rows.clear()
        self.assertEqual([], await self.use_case.get_summaries())
