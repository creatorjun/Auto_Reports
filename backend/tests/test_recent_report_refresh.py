# backend/tests/test_recent_report_refresh.py
import asyncio
import json
import unittest
from contextlib import asynccontextmanager
from dataclasses import fields, replace
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx

from src.application.ports.job_repository import JobRepository
from src.application.ports.report_repository import ReportRepository
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.get_report import GetReportUseCase
from src.application.use_cases.trigger_report import TriggerReportUseCase
from src.application.widgets.collector_factory import CollectorEntry
from src.application.widgets.recent_collector import RecentCollector
from src.bootstrap.container import Container
from src.domain.constants import KST
from src.domain.entities.job import JobStatus
from src.domain.entities.report import NewReport, Report
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.external.jira_client import JiraClient
from src.infrastructure.job_runner import JobRunner
from src.infrastructure.report_cache import ReportLruCache


class RecentReportRefreshTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.version = 1
        self.fail_second_page = False
        self.requests = []
        self.jira = JiraClient("https://jira.example.test", "user", "token")
        self.addAsyncCleanup(self.jira.aclose)
        await self.jira._client.aclose()
        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(self.respond))
        self.cache = ReportLruCache()
        self.addAsyncCleanup(self.cache.aclose)
        self.builder = WidgetQueryBuilder(QueryConfig(
            project_key="T", issue_types=["인시던트"], active_statuses=["처리 중"],
            closed_statuses=["Closed"], sla_threshold_days=30, year_start=2026,
            redeployment_flag_field="cf[1]", redeployment_month_field="cf[2]",
        ))
        self.assembler = ReportAssembler(
            self.builder,
            lambda queries, now: [CollectorEntry(WidgetId.RECENT_ISSUES, RecentCollector(self.jira, queries, now))],
            lambda queries, now: [],
        )
        initial = await self.assembler.collect(
            datetime(2026, 10, 18, 23, 59, 59, tzinfo=KST),
            week_start_override=datetime(2026, 10, 12, tzinfo=KST),
        )
        self.latest = self.as_report(initial, 17)
        self.repository = AsyncMock(spec=ReportRepository)
        self.repository.find_latest.side_effect = lambda: self.latest
        self.repository.find_annual.return_value = None
        self.repository.save.side_effect = self.save
        self.repository.update_widgets.side_effect = self.update
        await self.cache.set(self.latest.id, self.latest)
        await self.cache.set_latest_id(self.latest.id)

        @asynccontextmanager
        async def session():
            yield Mock()

        @asynccontextmanager
        async def reports():
            yield GetReportUseCase(self.repository, self.cache)

        self.container = Container.__new__(Container)
        self.container._jira = self.jira
        self.container._assembler = self.assembler
        self.container._analyzer = Mock(analyze=AsyncMock(return_value=None))
        self.container._cache = self.cache
        self.container._database = Mock(session=session)
        self.container._settings = Mock(report_retention_weeks=0)
        self.container._notify_todo = None
        self.container._notify_tac = None
        self.records = {}
        jobs = AsyncMock(spec=JobRepository)
        jobs.save.side_effect = lambda record: self.records.update({record.job_id: record})
        jobs.find.side_effect = self.records.get
        self.runner = JobRunner(self.container.generate_report, jobs)
        self.addAsyncCleanup(self.runner.aclose)
        self.trigger = TriggerReportUseCase(self.runner, reports)
        self.repository_patch = patch("src.bootstrap.container.ReportRepositoryImpl", return_value=self.repository)
        self.repository_patch.start()
        self.addCleanup(self.repository_patch.stop)

    @staticmethod
    def as_report(report, report_id):
        return Report(id=report_id, **{field.name: getattr(report, field.name) for field in fields(NewReport)})

    async def save(self, report):
        self.latest = self.as_report(report, self.latest.id + 1)
        return self.latest

    async def update(self, report_id, report):
        self.latest = self.as_report(report, report_id)
        return self.latest

    def respond(self, request):
        self.assertEqual("/rest/api/3/search/jql", request.url.path)
        payload = json.loads(request.content)
        self.requests.append(payload)
        second_page = "nextPageToken" in payload
        if second_page and self.fail_second_page:
            return httpx.Response(503)
        key = ("T-2" if self.version == 1 else "T-3") if second_page else "T-1"
        status = "이슈 리뷰 중" if self.version == 1 else "처리 중"
        response = {"issues": [{"key": key, "fields": {
            "summary": f"Issue {key} v{self.version}", "status": {"name": status},
            "issuetype": {"name": "인시던트"}, "created": "2026-10-13T09:00:00.000+0900",
        }}]}
        if not second_page:
            response["nextPageToken"] = f"page-2-v{self.version}"
        return httpx.Response(200, json=response)

    async def rerun(self):
        result = await self.trigger.execute(rerun_latest=True)
        await asyncio.wait_for(asyncio.gather(*self.runner._tasks), timeout=3)
        return self.records[result.job_id]

    def assert_recent(self, report, version):
        details = report.widgets[WidgetId.RECENT_ISSUES].data.issue_details
        self.assertEqual(["T-1", "T-2" if version == 1 else "T-3"], [issue.key for issue in details])
        self.assertEqual(["이슈 리뷰 중" if version == 1 else "처리 중"] * 2, [issue.status for issue in details])
        self.assertEqual(f"Issue T-1 v{version}", details[0].summary)

    async def test_rerun_uses_last_saved_period_and_requeries_every_recent_issue_page(self):
        older = replace(self.latest, id=16, week_start=date(2026, 10, 5), week_end=date(2026, 10, 11))
        await self.cache.set(older.id, older)
        await self.cache.set_latest_id(older.id)
        original_jql = self.latest.widgets[WidgetId.RECENT_ISSUES].jql
        self.version = 2

        result = await self.rerun()

        self.assertEqual(JobStatus.DONE, result.status)
        self.assertEqual(18, result.report_id)
        self.assertEqual((date(2026, 10, 12), date(2026, 10, 18)), (self.latest.week_start, self.latest.week_end))
        self.assert_recent(self.latest, 2)
        self.assert_recent(await self.cache.get(result.report_id), 2)
        self.assertEqual(4, len(self.requests))
        self.assertTrue(all(request["jql"] == original_jql for request in self.requests))
        self.assertEqual("page-2-v2", self.requests[-1]["nextPageToken"])

    async def test_automatic_refresh_cannot_restore_old_recent_issue_cache_after_manual_rerun(self):
        self.version = 2
        await self.rerun()
        self.assert_recent(self.latest, 2)
        before = len(self.requests)

        await self.container.refresh_report()

        self.assertEqual(before + 2, len(self.requests))
        self.assert_recent(self.latest, 2)
        self.assert_recent(await self.cache.get(self.latest.id), 2)
        self.assertEqual(18, self.latest.id)

    async def test_failed_recent_issue_page_preserves_saved_report_for_manual_and_automatic_refresh(self):
        previous = self.latest
        self.version = 2
        self.fail_second_page = True

        with self.assertLogs("src.infrastructure.job_runner", level="ERROR"):
            result = await self.rerun()
        self.assertEqual(JobStatus.ERROR, result.status)
        self.assertIs(previous, self.latest)
        self.repository.save.assert_not_awaited()

        with self.assertRaises(RuntimeError):
            await self.container.refresh_report()
        self.repository.update_widgets.assert_not_awaited()
        self.assertIs(previous, self.latest)
        self.assert_recent(await self.cache.get(previous.id), 1)
