# backend/tests/test_report_chart_issues.py
import dataclasses
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraAssetReference, JiraChartIssuePage, JiraIssue, JiraIssueField
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.use_cases.get_report_chart_issues import GetReportChartIssuesUseCase
from src.domain.entities.report import Report, ReportScope
from src.domain.entities.report_chart import ReportChartKind, ReportChartSelection
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    MonthlyEntry, RedeploymentAnalyticsWidgetData, ResolutionTypeEntry,
    ResolutionTypeWidgetData, SlaMonthlyTypeStats, SlaMonthlyWidgetData, TypeCountWidgetData,
)
from src.domain.value_objects.widget_id import WidgetId
from src.presentation.schemas.report_chart_schema import ReportChartIssueResultSchema


def chart_issue(key: str, issue_type: str, created: str = "2024-01-01T09:00:00", resolved: str = "2024-01-03T09:00:00") -> JiraIssue:
    return JiraIssue(
        key=key, summary=f"{key} 제목", issue_type=issue_type,
        status="Closed", created=created, resolved=resolved,
    )


class StoredReport:
    def __init__(self, report):
        self.report = report

    async def get_by_id(self, report_id):
        return self.report if self.report and self.report.id == report_id else None


class ChartJira:
    def __init__(self, issues, has_more=False):
        self.issues = issues
        self.has_more = has_more
        self.calls = []

    async def get_report_chart_issues(self, jql, max_results, fields, with_sla=False, with_redeployment=False):
        self.calls.append((jql, max_results, fields, with_sla, with_redeployment))
        return JiraChartIssuePage(self.issues, self.has_more)

    async def get_report_chart_asset_labels(self, references):
        return {JiraAssetReference("workspace", "1"): "파트너 A"}


class ReportChartIssuesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        stats = MonthlyEntry(
            month="2024-01", year=2024, month_num=1, rate=75, met=3, total=4,
            by_type={"개선": SlaMonthlyTypeStats(2, 3)},
            always_included=SlaMonthlyTypeStats(1, 1),
        )
        widgets = {
            WidgetId.YEARLY_CREATED: WidgetResult("생성", 4, data=TypeCountWidgetData(issue_types=["개선", "인시던트", "케이스"])),
            WidgetId.SLA_INITIAL_RESPONSE: WidgetResult("응답 SLA", 0, data=SlaMonthlyWidgetData(monthly=[stats])),
            WidgetId.SLA_RESOLUTION_MONTHLY: WidgetResult("해결 SLA", 0, data=SlaMonthlyWidgetData(monthly=[stats])),
            WidgetId.AVG_RESOLUTION_TYPE: WidgetResult("처리일", 5, data=ResolutionTypeWidgetData(
                by_type={"개선": ResolutionTypeEntry(2, 48, 5)},
                by_semester={"h1": {"개선": ResolutionTypeEntry(2, 48, 3)}},
            )),
            WidgetId.REDEPLOYMENT_ANALYTICS: WidgetResult("재배포", 2, data=RedeploymentAnalyticsWidgetData(
                resolved_total=20, redeployment_total=2, redeployment_rate=10,
                analytics_total=1, classification_complete=True,
                partner_matrix={"파트너 A": {"개선": 1, "CVE": 1}},
            )),
        }
        self.report = Report(id=7, week_start=datetime.date(2024, 1, 1), week_end=datetime.date(2024, 12, 31), report_date="2025-01-01 12:00", scope=ReportScope.ANNUAL, report_year=2024, widgets=widgets)
        self.builder = WidgetQueryBuilder(QueryConfig("TACEA", ["개선"], [], [], 30, 2026))

    def use_case(self, jira):
        return GetReportChartIssuesUseCase(StoredReport(self.report), jira, self.builder)

    async def test_historical_snapshot_returns_live_sla_issues_and_preserves_stored_counts(self):
        first = dataclasses.replace(chart_issue("T-1", "개선"), initial_response_breached=True)
        second = dataclasses.replace(chart_issue("T-2", "개선"), initial_response_breached=True)
        third = chart_issue("T-3", "케이스")
        before = dataclasses.asdict(self.report)
        jira = ChartJira([first, second, third])
        result = await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.SLA_INITIAL, month=1, sla_status="violated"))
        self.assertEqual(["T-1", "T-2"], [issue.key for issue in result.issues])
        self.assertEqual((1, 2), (result.snapshot_count, result.current_count))
        self.assertEqual((3, True, False), (result.source_total, result.source_total_exact, result.truncated))
        self.assertEqual(before, dataclasses.asdict(self.report))
        self.assertIn('created >= "2024-01-01"', jira.calls[0][0])
        self.assertEqual((500, True), (jira.calls[0][1], jira.calls[0][3]))
        self.assertIsInstance(jira.calls[0][2], frozenset)
        self.assertIn(JiraIssueField.STATUS, jira.calls[0][2])
        self.assertEqual("current_jira", ReportChartIssueResultSchema.model_validate(result).source)

    async def test_empty_type_selection_keeps_hidden_and_uncontrolled_types(self):
        jira = ChartJira([chart_issue("T-1", "개선"), chart_issue("T-2", "케이스"), chart_issue("T-3", "라이선스")])
        result = await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.SLA_RESOLUTION, month=1, selected_types=()))
        self.assertEqual(["T-2"], [issue.key for issue in result.issues])
        self.assertEqual(1, result.snapshot_count)
        self.assertTrue(result.issues[0].sla_met)

    async def test_resolution_filters_after_sampling_and_reuses_collector_elapsed_formula(self):
        jira = ChartJira([
            chart_issue("T-1", "개선"),
            chart_issue("T-2", "개선", resolved="2024-07-02T09:00:00"),
            chart_issue("T-3", "인시던트"),
            chart_issue("T-4", "개선", created=""),
        ], has_more=True)
        result = await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.RESOLUTION_TYPE, issue_type="개선", semester="h1"))
        self.assertEqual(["T-1"], [issue.key for issue in result.issues])
        self.assertEqual(48, result.issues[0].elapsed_hours)
        self.assertEqual(3, result.snapshot_count)
        self.assertTrue(result.truncated)
        self.assertFalse(result.source_total_exact)
        self.assertEqual(5, result.source_total)
        self.assertIn('resolved < "2025-01-01" ORDER BY resolved DESC', jira.calls[0][0])
        self.assertNotIn('issuetype = "개선"', jira.calls[0][0])

    async def test_resolution_details_query_includes_the_reports_final_day(self):
        self.report = dataclasses.replace(
            self.report, report_year=2026,
            week_start=datetime.date(2026, 1, 1),
            week_end=datetime.date(2026, 9, 10),
        )
        jira = ChartJira([chart_issue(
            "T-END", "개선", created="2026-09-09T23:59:59+09:00",
            resolved="2026-09-10T23:59:59+09:00",
        )])

        result = await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.RESOLUTION_TYPE))

        self.assertEqual(["T-END"], [issue.key for issue in result.issues])
        self.assertEqual(24, result.issues[0].elapsed_hours)
        self.assertIn(
            'resolved >= "2026-01-01" AND resolved < "2026-09-11" ORDER BY resolved DESC',
            jira.calls[0][0],
        )

    async def test_partner_returns_cve_issue_missing_from_legacy_analytics_list(self):
        issue = dataclasses.replace(
            chart_issue("T-CVE", "CVE"),
            partner_references=(JiraAssetReference("workspace", "1"),),
            redeployment_month="2024-02",
        )
        jira = ChartJira([issue])
        result = await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.REDEPLOYMENT, partner="파트너 A", issue_type="CVE"))
        self.assertEqual(["T-CVE"], [issue.key for issue in result.issues])
        self.assertEqual(1, result.snapshot_count)
        self.assertIsNone(result.collection_limit)
        self.assertIsNone(jira.calls[0][1])
        self.assertTrue(jira.calls[0][4])

    async def test_selection_text_never_becomes_jql(self):
        jira = ChartJira([])
        await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.RESOLUTION_TYPE, issue_type='x" OR project = SECRET'))
        self.assertNotIn("SECRET", jira.calls[0][0])

    async def test_sla_status_filter_uses_live_status_and_stored_status_breakdown(self):
        stats = self.report.widgets[WidgetId.SLA_INITIAL_RESPONSE].data.monthly[0]
        stats.by_status_type = {
            "Closed": {"개선": SlaMonthlyTypeStats(1, 2), "케이스": SlaMonthlyTypeStats(1, 1)},
            "할 일": {"개선": SlaMonthlyTypeStats(1, 1)},
        }
        jira = ChartJira([
            dataclasses.replace(chart_issue("T-1", "개선"), initial_response_breached=True),
            dataclasses.replace(chart_issue("T-2", "개선"), status="할 일", initial_response_breached=True),
        ])
        result = await self.use_case(jira).execute(7, ReportChartSelection(
            ReportChartKind.SLA_INITIAL, month=1, selected_statuses=("Closed",), sla_status="violated",
        ))
        self.assertEqual(["T-1"], [issue.key for issue in result.issues])
        self.assertEqual(1, result.snapshot_count)
        self.assertNotIn('status = "Closed"', jira.calls[0][0])

    async def test_resolution_status_filter_uses_the_selected_semester_breakdown(self):
        data = self.report.widgets[WidgetId.AVG_RESOLUTION_TYPE].data
        data.by_status_type = {"Closed": {"개선": ResolutionTypeEntry(2, 48, 4)}}
        data.by_semester_status_type = {"h1": {"Closed": {"개선": ResolutionTypeEntry(2, 48, 2)}}}
        jira = ChartJira([
            chart_issue("T-1", "개선"),
            dataclasses.replace(chart_issue("T-2", "개선"), status="재오픈"),
        ])
        result = await self.use_case(jira).execute(7, ReportChartSelection(
            ReportChartKind.RESOLUTION_TYPE, issue_type="개선", semester="h1", selected_statuses=("Closed",),
        ))
        self.assertEqual(["T-1"], [issue.key for issue in result.issues])
        self.assertEqual(2, result.snapshot_count)

    async def test_empty_status_selection_returns_zero_for_current_and_snapshot_counts(self):
        for chart, kwargs in (
            (ReportChartKind.SLA_INITIAL, {"month": 1}),
            (ReportChartKind.RESOLUTION_TYPE, {}),
        ):
            with self.subTest(chart=chart):
                result = await self.use_case(ChartJira([chart_issue("T-1", "개선")])).execute(
                    7, ReportChartSelection(chart, selected_statuses=(), **kwargs),
                )
                self.assertEqual([], result.issues)
                self.assertEqual((0, 0), (result.snapshot_count, result.current_count))

    async def test_status_filter_does_not_reuse_unfiltered_legacy_snapshot_count(self):
        for chart, kwargs in (
            (ReportChartKind.SLA_INITIAL, {"month": 1}),
            (ReportChartKind.RESOLUTION_TYPE, {"semester": "h1"}),
        ):
            with self.subTest(chart=chart):
                result = await self.use_case(ChartJira([chart_issue("T-1", "개선")])).execute(
                    7, ReportChartSelection(chart, selected_statuses=("Closed",), **kwargs),
                )
                self.assertEqual(1, result.current_count)
                self.assertIsNone(result.snapshot_count)

    async def test_partner_label_failure_never_returns_successful_empty_details(self):
        class FailingPartnerJira(ChartJira):
            async def get_report_chart_asset_labels(self, references):
                raise RuntimeError("Assets unavailable")
        with self.assertRaisesRegex(RuntimeError, "Assets unavailable"):
            await self.use_case(FailingPartnerJira([])).execute(7, ReportChartSelection(ReportChartKind.REDEPLOYMENT, partner="파트너 A"))

    async def test_missing_nonannual_and_out_of_period_reports_fail_before_jira(self):
        jira = ChartJira([])
        with self.assertRaises(EntityNotFoundError):
            await self.use_case(jira).execute(8, ReportChartSelection(ReportChartKind.RESOLUTION_TYPE))
        self.report = dataclasses.replace(self.report, scope=ReportScope.STANDARD)
        with self.assertRaises(ValueError):
            await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.RESOLUTION_TYPE))
        self.report = dataclasses.replace(self.report, scope=ReportScope.ANNUAL, week_end=datetime.date(2024, 6, 30))
        with self.assertRaises(ValueError):
            await self.use_case(jira).execute(7, ReportChartSelection(ReportChartKind.SLA_INITIAL, month=7))
        self.assertEqual([], jira.calls)

    def test_invalid_cross_dimension_selections_are_rejected(self):
        for kwargs in ({"chart": ReportChartKind.SLA_INITIAL}, {"chart": ReportChartKind.RESOLUTION_TYPE, "partner": "파트너"}, {"chart": ReportChartKind.REDEPLOYMENT, "month": 1, "cause": "오류"}, {"chart": ReportChartKind.SLA_INITIAL, "month": 1, "semester": "h2"}, {"chart": ReportChartKind.REDEPLOYMENT, "selected_statuses": ()}, {"chart": ReportChartKind.RESOLUTION_TYPE, "selected_statuses": ("\n",)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ReportChartSelection(**kwargs)
