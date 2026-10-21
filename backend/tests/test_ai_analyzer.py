# backend/tests/test_ai_analyzer.py
import json
import unittest
from dataclasses import replace
from datetime import date
from unittest.mock import AsyncMock

from src.application.ports.ai_port import AiPort
from src.application.services.ai_analyzer import AiAnalyzer
from src.domain.entities.report import NewReport, ReportScope
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    CreatedResolvedIssueDetail,
    CreatedVsResolvedWidgetData,
    IssueDetail,
    MonthlyCountEntry,
    MonthlyCountWidgetData,
    MonthlyEntry,
    RecentIssueDetail,
    RecentIssueWidgetData,
    RedeploymentAnalyticsWidgetData,
    RedeploymentIssueDetail,
    ResolutionTypeEntry,
    ResolutionTypeWidgetData,
    ResolvedIssueDetail,
    SimpleIssueWidgetData,
    SlaDelayIssueDetail,
    SlaDelayWidgetData,
    SlaMetVsViolatedWidgetData,
    SlaMonthlyWidgetData,
    StageDurationIssue,
    TypeCountWidgetData,
)
from src.domain.value_objects.ai_analysis import AiAnalysis
from src.domain.value_objects.widget_id import WidgetId


class AiAnalyzerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ai = AsyncMock(spec=AiPort)
        self.analysis = AiAnalysis("검증된 요약", [], ["추가 확인"], "warning")
        self.ai.analyze.return_value = self.analysis
        self.analyzer = AiAnalyzer(self.ai)
        self.report = NewReport(date(2026, 10, 1), date(2026, 10, 31), "2026-10-31 23:59")

    async def context(self, widgets: dict, **changes) -> dict:
        report = replace(self.report, widgets=widgets, **changes)
        result = await self.analyzer.analyze(report)
        self.assertIs(self.analysis, result)
        prompt = self.ai.analyze.await_args.args[0]
        return json.loads(prompt.split("[보고서 근거 JSON]\n", 1)[1])

    @staticmethod
    def widget(context: dict, widget_id: WidgetId) -> dict:
        return next(widget for widget in context["widgets"] if widget["id"] == widget_id.value)

    async def test_disabled_or_absent_provider_never_invokes_analysis(self) -> None:
        self.assertIsNone(await AiAnalyzer(self.ai, enabled=False).analyze(self.report))
        self.assertIsNone(await AiAnalyzer(None).analyze(self.report))
        self.ai.analyze.assert_not_awaited()

    async def test_current_widget_contract_passes_exact_month_counts_and_named_saved_query(self) -> None:
        query = 'project = T AND created >= "2026-10-01" AND created < "2026-11-01"'
        context = await self.context({
            WidgetId.CREATED_VS_RESOLVED: WidgetResult("과거 주간 이름", 7, query, CreatedVsResolvedWidgetData(
                created=7, resolved=4,
                created_details=[CreatedResolvedIssueDetail("T-1", "비공개 제목", "개선", "할 일", "2026-10-01")],
                resolved_details=[ResolvedIssueDetail("T-2", "비공개 제목", "개선", "2026-10-02")],
            )),
            WidgetId.YEARLY_CREATED: WidgetResult("누적", 100, data=TypeCountWidgetData(by_type={"개선": 90}, always_included=10)),
        })
        flow = self.widget(context, WidgetId.CREATED_VS_RESOLVED)
        self.assertEqual("selected_period", flow["basis"])
        self.assertEqual((7, 4), (flow["metrics"]["created"], flow["metrics"]["resolved"]))
        self.assertEqual(["T-1"], flow["metrics"]["created_evidence_keys"])
        self.assertEqual(["T-2"], flow["metrics"]["resolved_evidence_keys"])
        self.assertEqual([{"name": "CREATED_VS_RESOLVED", "basis": "selected_period", "jql": query}], context["queries"])
        self.assertEqual("2026-10-01", context["report"]["period_start"])
        self.assertEqual("2026-10-31", context["report"]["period_end_inclusive"])
        self.assertEqual("Asia/Seoul", context["report"]["timezone"])
        self.assertIsNone(context["report"]["collected_at"])
        self.assertFalse(self.widget(context, WidgetId.REDEPLOYMENT_ANALYTICS)["applicable"])
        yearly = self.widget(context, WidgetId.YEARLY_CREATED)
        self.assertEqual("calendar_year", yearly["basis"])
        self.assertEqual(100, yearly["metrics"]["count"])
        self.assertNotIn("비공개 제목", self.ai.analyze.await_args.args[0])
        self.assertNotIn("이번 주 생성", self.ai.analyze.await_args.args[0])
        self.assertNotIn("2026-10-31 23:59", self.ai.analyze.await_args.args[0])

    async def test_historical_annual_scope_and_missing_metrics_are_explicit(self) -> None:
        context = await self.context({}, scope=ReportScope.ANNUAL, report_year=2024,
                                     week_start=date(2024, 1, 1), week_end=date(2024, 12, 31))
        self.assertEqual("annual", context["report"]["scope"])
        self.assertEqual(2024, context["report"]["calendar_statistics_year"])
        self.assertTrue(all(not widget["available"] for widget in context["widgets"]))
        self.assertTrue(self.widget(context, WidgetId.REDEPLOYMENT_ANALYTICS)["applicable"])
        self.assertNotIn("sla_met", context)
        self.assertNotIn("avg_resolution_days", self.ai.analyze.await_args.args[0])
        self.assertIn("근거가 없으면 빈 배열", self.ai.analyze.await_args.args[0])

    async def test_sla_overlap_keeps_unique_total_without_fabricating_denominator(self) -> None:
        data = SlaMetVsViolatedWidgetData(initial_response_violations=4, resolution_violations=5, both_violations=3)
        context = await self.context({WidgetId.SLA_MET_VS_VIOLATED: WidgetResult("SLA", 6, data=data)})
        widget = self.widget(context, WidgetId.SLA_MET_VS_VIOLATED)
        self.assertEqual("current_unresolved_snapshot", widget["basis"])
        metrics = widget["metrics"]
        self.assertEqual(6, metrics["unique_violating_tickets"])
        self.assertTrue(metrics["counts_consistent"])
        self.assertIsNone(metrics["population_count"])
        self.assertIsNone(metrics["violation_rate"])
        context = await self.context({WidgetId.SLA_MET_VS_VIOLATED: WidgetResult("SLA", 9, data=data)})
        self.assertFalse(self.widget(context, WidgetId.SLA_MET_VS_VIOLATED)["metrics"]["counts_consistent"])

    async def test_state_distribution_is_not_a_delay_cause(self) -> None:
        context = await self.context({WidgetId.SLA_DELAY_REASON: WidgetResult("지연 사유", 2, data=SlaDelayWidgetData(
            by_status={"자료 요청 중": 2}, by_status_details={"자료 요청 중": [
                SlaDelayIssueDetail("T-3", "고객과 담당자 이름", "개선", "자료 요청 중", "2026-10-01"),
            ]},
        ))})
        metrics = self.widget(context, WidgetId.SLA_DELAY_REASON)["metrics"]
        self.assertEqual({"자료 요청 중": 2}, metrics["current_status_distribution"])
        self.assertEqual(["T-3"], metrics["evidence_keys"])
        self.assertIn("지연 원인", metrics["limitation"])
        self.assertNotIn("고객과 담당자 이름", self.ai.analyze.await_args.args[0])

    async def test_age_samples_are_bounded_but_total_and_age_statistics_use_all_details(self) -> None:
        details = [IssueDetail(f"T-{index}", "고객 비밀", "개선", "할 일", "2026-01-01", index)
                   for index in range(1, 16)]
        context = await self.context({WidgetId.ISSUE_REVIEW: WidgetResult("리뷰", 15, data=SimpleIssueWidgetData(details))})
        metrics = self.widget(context, WidgetId.ISSUE_REVIEW)["metrics"]
        self.assertEqual((15, 15, 15, 8), (metrics["count"], metrics["detail_count"], metrics["maximum_age_days"], metrics["median_age_days"]))
        self.assertEqual([f"T-{index}" for index in range(15, 5, -1)], metrics["evidence_keys"])
        self.assertIn("상태 체류시간이나 SLA 초과시간이 아님", metrics["age_definition"])
        self.assertNotIn("고객 비밀", self.ai.analyze.await_args.args[0])

    async def test_current_issue_personal_data_is_excluded(self) -> None:
        data = RecentIssueWidgetData([RecentIssueDetail(
            key="T-4", summary="숨겨야 할 상세 제목", type="개선", status="할 일", stage_index=0,
            created="2026-10-01", elapsed_days=20, reporter="개인 보고자", tac_team="개인 팀",
            tac_assignee="개인 담당자", reporter_account_id="reporter-private-id",
            tac_team_account_id="team-private-id", tac_assignee_account_id="assignee-private-id",
        )])
        await self.context({WidgetId.RECENT_ISSUES: WidgetResult("최근", 1, data=data)})
        prompt = self.ai.analyze.await_args.args[0]
        for private in ("숨겨야 할 상세 제목", "개인 보고자", "개인 팀", "개인 담당자", "reporter-private-id", "team-private-id", "assignee-private-id"):
            self.assertNotIn(private, prompt)

    async def test_stage_bottleneck_evidence_includes_coverage_and_robust_duration_statistics(self) -> None:
        data = ResolutionTypeWidgetData(
            by_type={"개선": ResolutionTypeEntry(avg_days=2, avg_hours=48, count=5)},
            stage_issues=[
                StageDurationIssue("T-1", "개선", "Closed", "2026-10-15", {"자료 요청 중": 1}),
                StageDurationIssue("T-2", "개선", "Closed", "2026-10-16", {"자료 요청 중": 3}),
                StageDurationIssue("T-3", "개선", "Closed", "2026-10-17", {"자료 요청 중": 20}),
                StageDurationIssue("T-4", "개선", "Closed", "2026-10-18", {"자료 요청 중": float("nan")}),
            ],
        )
        context = await self.context({WidgetId.AVG_RESOLUTION_TYPE: WidgetResult("처리시간", 5, data=data)})
        metrics = self.widget(context, WidgetId.AVG_RESOLUTION_TYPE)["metrics"]
        self.assertEqual({"count": 5, "average_hours": 48, "average_days": 2}, metrics["by_type"]["개선"])
        history = metrics["stage_history"]
        self.assertEqual((5, 3, 2), (history["resolved_issue_count"], history["history_issue_count"], history["missing_or_invalid_history_count"]))
        self.assertEqual({
            "status": "자료 요청 중", "sample_count": 3, "total_hours": 24,
            "average_hours": 8, "median_hours": 3, "maximum_hours": 20,
            "evidence_keys": ["T-3", "T-2", "T-1"],
        }, history["stages"][0])

    async def test_absent_history_and_empty_population_do_not_fabricate_zero_durations(self) -> None:
        for stage_issues in (None, []):
            context = await self.context({WidgetId.AVG_RESOLUTION_TYPE: WidgetResult(
                "처리시간", 3, data=ResolutionTypeWidgetData(stage_issues=stage_issues),
            )})
            history = self.widget(context, WidgetId.AVG_RESOLUTION_TYPE)["metrics"]["stage_history"]
            self.assertEqual(stage_issues is not None, history["available"])
            self.assertNotIn("average_hours", history)
            if stage_issues is not None:
                self.assertEqual(3, history["missing_or_invalid_history_count"])
                self.assertEqual([], history["stages"])

    async def test_monthly_metrics_keep_observed_denominators_and_empty_rates_unknown(self) -> None:
        context = await self.context({
            WidgetId.MONTHLY_CREATED: WidgetResult("월별", 4, data=MonthlyCountWidgetData([
                MonthlyCountEntry("2026-10", 2026, 10, 4),
            ])),
            WidgetId.SLA_INITIAL_RESPONSE: WidgetResult("SLA 월별", 0, data=SlaMonthlyWidgetData([
                MonthlyEntry("2026-10", 2026, 10, 75, 3, 4),
                MonthlyEntry("2026-11", 2026, 11, 0, 0, 0),
            ])),
        })
        self.assertEqual([{"month": "2026-10", "count": 4}], self.widget(context, WidgetId.MONTHLY_CREATED)["metrics"]["monthly"])
        monthly = self.widget(context, WidgetId.SLA_INITIAL_RESPONSE)["metrics"]["monthly"]
        self.assertEqual((4, 3, 1, 75), (monthly[0]["population_count"], monthly[0]["not_breached_count"], monthly[0]["violated_count"], monthly[0]["not_breached_rate"]))
        self.assertIsNone(monthly[1]["not_breached_rate"])

    async def test_redeployment_keeps_metrics_and_queries_without_people_or_customer_dimensions(self) -> None:
        data = RedeploymentAnalyticsWidgetData(
            resolved_total=10, redeployment_total=2, redeployment_rate=20, analytics_total=2,
            classification_complete=True, by_assignee={"비공개 담당자": 2}, partner_matrix={"고객 파트너": {"개선": 2}},
            latest_issues=[RedeploymentIssueDetail("T-1", "비공개 제목", "개선", "높음", "2026-10-01", "2026-10", "원인 입력", "비공개 담당자")],
            source_jqls={"resolved": "project = T AND status = Closed"},
        )
        context = await self.context({WidgetId.REDEPLOYMENT_ANALYTICS: WidgetResult("재배포", 2, data=data)})
        self.assertEqual(20, self.widget(context, WidgetId.REDEPLOYMENT_ANALYTICS)["metrics"]["redeployment_rate"])
        self.assertEqual("REDEPLOYMENT_resolved", context["queries"][0]["name"])
        for private in ("비공개 담당자", "고객 파트너", "비공개 제목", "원인 입력"):
            self.assertNotIn(private, self.ai.analyze.await_args.args[0])

    async def test_provider_failure_is_left_for_generation_failure_isolation(self) -> None:
        self.ai.analyze.side_effect = RuntimeError("provider unavailable")
        with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
            await self.analyzer.analyze(self.report)
