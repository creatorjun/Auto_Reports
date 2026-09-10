# backend/tests/test_issue_age.py
import copy
import datetime
import pathlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.jira_port import JiraIssue
from src.application.ports.report_cache_port import ReportCachePort
from src.application.ports.report_repository import ReportRepository
from src.application.services.issue_age import (
    issue_created_display,
    issue_elapsed_days,
    with_current_issue_age,
)
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.get_report import GetReportUseCase
from src.application.widgets.count_collector import SimpleWithDetailsCollector
from src.domain.constants import KST
from src.domain.entities.report import Report, ReportScope
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    IssueDetail,
    RecentIssueDetail,
    RecentIssueWidgetData,
    SimpleIssueWidgetData,
    TypeCountWidgetData,
)
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory


NOW = datetime.datetime(2026, 9, 10, 0, 5, tzinfo=KST)
ISSUE_DATES = ["2026-09-10 00:01", "2026-09-09 23:59", "2026-08-31 12:00"]
AGED_WIDGETS = (
    WidgetId.ISSUE_REVIEW,
    WidgetId.DATA_REQUEST,
    WidgetId.RESULT_PENDING,
    WidgetId.RECENT_ISSUES,
)


class FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return NOW.replace(tzinfo=None)
        return NOW.astimezone(tz)


def historical_report() -> Report:
    widgets = {}
    for widget_id in AGED_WIDGETS:
        rows = []
        for index, created in enumerate(ISSUE_DATES):
            values = {
                "key": f"TACEA-{index + 1}",
                "summary": f"경과일 확인 {index + 1}",
                "type": "인시던트",
                "status": "할 일",
                "created": created,
                "elapsed_days": [-10, -9, 0][index],
            }
            if widget_id == WidgetId.RECENT_ISSUES:
                rows.append(RecentIssueDetail(**values, stage_index=0, reporter="보고자"))
            else:
                rows.append(IssueDetail(**values))
        data = RecentIssueWidgetData(rows) if widget_id == WidgetId.RECENT_ISSUES else SimpleIssueWidgetData(rows)
        widgets[widget_id] = WidgetResult(name=f"확인 {widget_id}", total=3, jql="project = TACEA", data=data)
    widgets[WidgetId.YEARLY_CREATED] = WidgetResult(
        name="누적 생성", total=37, jql="created >= 2026-01-01", data=TypeCountWidgetData(by_type={"인시던트": 37}),
    )
    return Report(
        id=7,
        week_start=datetime.date(2026, 8, 1),
        week_end=datetime.date(2026, 8, 31),
        report_date="2026-08-31 23:59",
        created_at=datetime.datetime(2026, 9, 1, 12, tzinfo=KST),
        widgets=widgets,
        scope=ReportScope.STANDARD,
    )


class IssueAgeTest(unittest.TestCase):
    def test_calendar_days_use_current_kst_date_and_respect_timestamp_offsets(self):
        cases = [
            ("2026-09-10T00:01:00.000+0900", 0),
            ("2026-09-09T23:59:00.000+0900", 1),
            ("2026-08-31 12:00", 10),
            ("2026-09-09T15:01:00Z", 0),
            ("2026-09-09T14:59:00+00:00", 1),
            ("2026-09-09T08:01:00-0700", 0),
            ("2026-09-10", 0),
        ]
        for created, expected in cases:
            with self.subTest(created=created):
                self.assertEqual(expected, issue_elapsed_days(created, NOW))
                self.assertEqual(expected, issue_elapsed_days(created, NOW.astimezone(datetime.timezone.utc)))

    def test_future_missing_and_invalid_dates_never_produce_negative_values(self):
        for created in (None, "", "invalid", "2026-02-30 12:00", "2026-09-11 12:00"):
            with self.subTest(created=created):
                self.assertEqual(0, issue_elapsed_days(created, NOW))

    def test_created_display_normalizes_jira_and_utc_timestamps_to_kst(self):
        cases = [
            ("2026-09-10T00:01:30.000+0900", "2026-09-10 00:01"),
            ("2026-09-09T15:01:30Z", "2026-09-10 00:01"),
            ("2026-09-09T08:01:30-0700", "2026-09-10 00:01"),
            ("2026-09-10 00:01", "2026-09-10 00:01"),
            (None, ""),
            ("", ""),
            ("invalid", ""),
            ("2026-02-30T12:00:00+0900", ""),
        ]
        for created, expected in cases:
            with self.subTest(created=created):
                self.assertEqual(expected, issue_created_display(created))

    def test_historical_report_ages_are_recomputed_without_mutating_stored_snapshot(self):
        report = historical_report()
        original = copy.deepcopy(report)

        result = with_current_issue_age(report, NOW)

        self.assertIsNot(result, report)
        self.assertIsNot(result.widgets, report.widgets)
        self.assertEqual(original, report)
        for widget_id in AGED_WIDGETS:
            with self.subTest(widget_id=widget_id):
                actual = result.widgets[widget_id]
                stored = report.widgets[widget_id]
                self.assertIsNot(actual, stored)
                self.assertIsNot(actual.data, stored.data)
                self.assertIsNot(actual.data.issue_details, stored.data.issue_details)
                self.assertEqual([0, 1, 10], [row.elapsed_days for row in actual.data.issue_details])
                self.assertEqual((stored.name, stored.total, stored.jql), (actual.name, actual.total, actual.jql))
                for actual_row, stored_row in zip(actual.data.issue_details, stored.data.issue_details):
                    self.assertIsNot(actual_row, stored_row)
                    actual_values = vars(actual_row).copy()
                    actual_values.pop("elapsed_days")
                    stored_values = vars(stored_row).copy()
                    stored_values.pop("elapsed_days")
                    self.assertEqual(stored_values, actual_values)
        self.assertEqual(report.widgets[WidgetId.YEARLY_CREATED], result.widgets[WidgetId.YEARLY_CREATED])
        for field in ("id", "week_start", "week_end", "report_date", "created_at", "scope", "report_year", "ai_analysis"):
            self.assertEqual(getattr(report, field), getattr(result, field))

    def test_default_clock_and_absent_report_or_widget_data_are_supported(self):
        report = historical_report()
        report.widgets[WidgetId.ISSUE_REVIEW].data = None
        report.widgets[WidgetId.DATA_REQUEST].data.issue_details = []
        del report.widgets[WidgetId.RESULT_PENDING]
        original = copy.deepcopy(report)

        with patch("src.application.services.issue_age.datetime", FixedDateTime):
            result = with_current_issue_age(report)
            self.assertIsNone(with_current_issue_age(None))

        self.assertEqual(original, report)
        self.assertIsNone(result.widgets[WidgetId.ISSUE_REVIEW].data)
        self.assertEqual([], result.widgets[WidgetId.DATA_REQUEST].data.issue_details)
        self.assertNotIn(WidgetId.RESULT_PENDING, result.widgets)
        self.assertEqual([0, 1, 10], [row.elapsed_days for row in result.widgets[WidgetId.RECENT_ISSUES].data.issue_details])


class GetReportIssueAgeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.report = historical_report()
        self.repository = AsyncMock(spec=ReportRepository)
        self.cache = AsyncMock(spec=ReportCachePort)
        self.repository.find_by_id.return_value = self.report
        self.repository.find_latest.return_value = self.report
        self.repository.find_annual.return_value = self.report
        self.cache.get.return_value = None
        self.cache.get_latest_id.return_value = None
        self.use_case = GetReportUseCase(self.repository, self.cache)

    async def assert_corrected(self, operation):
        original = copy.deepcopy(self.report)
        with patch("src.application.services.issue_age.datetime", FixedDateTime):
            result = await operation()
        self.assertEqual(original, self.report)
        self.assertIsNot(self.report, result)
        self.assertEqual([0, 1, 10], [row.elapsed_days for row in result.widgets[WidgetId.RECENT_ISSUES].data.issue_details])
        self.assertEqual(self.report.week_end, result.week_end)

    async def test_by_id_normalizes_cache_hit_without_mutating_cached_report(self):
        self.cache.get.return_value = self.report
        await self.assert_corrected(lambda: self.use_case.get_by_id(7))
        self.repository.find_by_id.assert_not_awaited()

    async def test_by_id_normalizes_database_fallback_without_mutating_cached_snapshot(self):
        await self.assert_corrected(lambda: self.use_case.get_by_id(7))
        self.repository.find_by_id.assert_awaited_once_with(7)
        self.cache.set.assert_awaited_once_with(7, self.report)

    async def test_latest_normalizes_cache_hit(self):
        self.cache.get_latest_id.return_value = 7
        self.cache.get.return_value = self.report
        await self.assert_corrected(self.use_case.get_latest)
        self.repository.find_latest.assert_not_awaited()

    async def test_latest_normalizes_cache_miss_and_missing_latest_id_database_paths(self):
        for latest_id in (7, None):
            with self.subTest(latest_id=latest_id):
                self.cache.reset_mock()
                self.repository.reset_mock()
                self.cache.get_latest_id.return_value = latest_id
                await self.assert_corrected(self.use_case.get_latest)
                self.repository.find_latest.assert_awaited_once_with()
                self.cache.set.assert_awaited_once_with(7, self.report)
                self.cache.set_latest_id.assert_awaited_once_with(7)

    async def test_annual_normalizes_database_report(self):
        await self.assert_corrected(lambda: self.use_case.get_annual(2026))
        self.repository.find_annual.assert_awaited_once_with(2026)
        self.cache.set.assert_awaited_once_with(7, self.report)

    async def test_missing_reports_remain_none_on_every_detail_lookup(self):
        self.repository.find_by_id.return_value = None
        self.repository.find_latest.return_value = None
        self.repository.find_annual.return_value = None
        for operation in (
            lambda: self.use_case.get_by_id(7),
            self.use_case.get_latest,
            lambda: self.use_case.get_annual(2026),
        ):
            with patch("src.application.services.issue_age.datetime", FixedDateTime):
                self.assertIsNone(await operation())
        self.cache.set.assert_not_awaited()


class IssueAgeJira:
    def __init__(self):
        self.queries = []
        self.issues = [
            JiraIssue(
                key=f"TACEA-{index + 1}",
                created=created,
                summary="수집 경과일 확인",
                issue_type="인시던트",
                status="할 일",
            )
            for index, created in enumerate((
                "2026-09-09T15:01:00Z",
                "2026-09-09T14:59:00Z",
                "2026-08-31T12:00:00.000+0900",
                "",
                "invalid",
            ))
        ]

    async def get_issues_with_assignees(self, jql, max_results):
        self.queries.append(jql)
        return self.issues

    async def get_issues(self, jql, max_results, fields):
        self.queries.append(jql)
        return self.issues


class CollectorIssueAgeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        config = QueryConfig(
            project_key="TACEA", issue_types=["인시던트"], active_statuses=["할 일"],
            closed_statuses=["Closed"], sla_threshold_days=30, year_start=2026,
        )
        self.end = datetime.datetime(2026, 8, 31, 23, 59, tzinfo=KST)
        self.query_builder = WidgetQueryBuilder(config)
        self.queries = self.query_builder.build(
            self.end, week_start_override=datetime.datetime(2026, 8, 1, tzinfo=KST),
        )

    def assert_details(self, result):
        rows = {row.key: row for row in result.data.issue_details}
        self.assertEqual(5, result.total)
        self.assertEqual([0, 1, 10, 0, 0], [rows[f"TACEA-{index + 1}"].elapsed_days for index in range(5)])
        self.assertEqual("2026-09-10 00:01", rows["TACEA-1"].created)
        self.assertEqual("2026-09-09 23:59", rows["TACEA-2"].created)
        self.assertEqual("", rows["TACEA-4"].created)
        self.assertEqual("", rows["TACEA-5"].created)

    async def test_factory_recent_collector_uses_current_date_for_historical_report(self):
        jira = IssueAgeJira()
        factory = WidgetCollectorFactory(jira)
        entry = next(entry for entry in factory.base_collectors(self.queries, NOW) if entry.widget_id == WidgetId.RECENT_ISSUES)

        result = await entry.collector.collect()

        self.assert_details(result)
        self.assertEqual([self.queries.w7_recent()], jira.queries)
        self.assertNotIn("created <=", jira.queries[0])

    async def test_status_collector_uses_kst_calendar_days_and_keeps_oldest_first(self):
        jira = IssueAgeJira()
        collector = SimpleWithDetailsCollector(jira, "이슈 리뷰 중", self.queries.w4_issue_review(), NOW)

        result = await collector.collect()

        self.assert_details(result)
        self.assertEqual("TACEA-3", result.data.issue_details[0].key)
        self.assertEqual([self.queries.w4_issue_review()], jira.queries)

    async def test_assembler_uses_collection_date_for_all_current_issue_widgets(self):
        period_start = datetime.datetime(2026, 8, 1, tzinfo=KST)
        for collected_at in (NOW, NOW.astimezone(datetime.timezone.utc)):
            with self.subTest(collected_at=collected_at):
                jira = IssueAgeJira()
                factory = WidgetCollectorFactory(jira)
                assembler = ReportAssembler(
                    query_builder=self.query_builder,
                    base_collector_factory=lambda queries, now: [
                        entry for entry in factory.base_collectors(queries, now)
                        if entry.widget_id in AGED_WIDGETS
                    ],
                    monthly_collector_factory=lambda queries, now: [],
                )

                report = await assembler.collect(
                    self.end, week_start_override=period_start, collected_at=collected_at,
                )

                self.assertEqual(set(AGED_WIDGETS), set(report.widgets))
                for widget_id in AGED_WIDGETS:
                    self.assert_details(report.widgets[widget_id])
                self.assertEqual(period_start.date(), report.week_start)
                self.assertEqual(self.end.date(), report.week_end)
                self.assertEqual("2026-08-31 23:59", report.report_date)
                self.assertCountEqual([
                    self.queries.w4_issue_review(), self.queries.w5_data_request(),
                    self.queries.w6_result_pending(), self.queries.w7_recent(),
                ], jira.queries)

    async def test_historical_yearly_titles_keep_report_year_when_collected_today(self):
        jira = IssueAgeJira()
        factory = WidgetCollectorFactory(jira)
        period_start = datetime.datetime(2025, 1, 1, tzinfo=KST)
        period_end = datetime.datetime(2025, 12, 31, 23, 59, tzinfo=KST)
        annual_ids = (WidgetId.YEARLY_CREATED, WidgetId.YEARLY_RESOLVED)
        assembler = ReportAssembler(
            query_builder=self.query_builder,
            base_collector_factory=lambda queries, now: [
                entry for entry in factory.base_collectors(queries, now)
                if entry.widget_id in annual_ids
            ],
            monthly_collector_factory=lambda queries, now: [],
        )

        report = await assembler.collect(
            period_end, week_start_override=period_start,
            annual_report_year=2025, collected_at=NOW,
        )

        self.assertEqual("2025년 누적 생성", report.widgets[WidgetId.YEARLY_CREATED].name)
        self.assertEqual("2025년 누적 해결", report.widgets[WidgetId.YEARLY_RESOLVED].name)
        for widget_id in annual_ids:
            self.assertIn('>= "2025-01-01"', report.widgets[widget_id].jql)
            self.assertIn('< "2026-01-01"', report.widgets[widget_id].jql)
        self.assertEqual(period_start.date(), report.week_start)
        self.assertEqual(period_end.date(), report.week_end)
        self.assertEqual("2025-12-31 23:59", report.report_date)
