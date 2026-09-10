# backend/tests/test_query_builder.py
import datetime
import operator
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.ports.jira_port import JiraIssue
from src.application.services.query_config import QueryConfig
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.resolution_collector import ResolutionCollector
from src.domain.value_objects.widget_id import WidgetId


class WidgetQueryBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = QueryConfig(
            project_key="TACEA",
            issue_types=["인시던트", "개선", "CVE", "서비스 요청", "라이선스"],
            active_statuses=["처리 중"],
            closed_statuses=["Closed", "반려됨", "중복 이슈", "취소됨"],
            sla_threshold_days=30,
            year_start=2026,
        )
        self.queries = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2026, 8, 18)
        )

    def test_yearly_created_excludes_license_requests(self) -> None:
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND created >= "2026-01-01" AND created < "2027-01-01"',
            self.queries.w1_yearly_created(),
        )

    def test_yearly_resolved_excludes_license_requests(self) -> None:
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND resolved >= "2026-01-01" AND resolved < "2027-01-01"',
            self.queries.w2_yearly_resolved(),
        )

    def test_historical_report_uses_the_requested_year(self) -> None:
        historical = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2024, 12, 31)
        )

        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND created >= "2024-01-01" AND created < "2025-01-01"',
            historical.w1_yearly_created(),
        )
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND resolved >= "2024-01-01" AND resolved < "2025-01-01"',
            historical.w2_yearly_resolved(),
        )

    def test_report_period_includes_the_full_end_date(self) -> None:
        periods = [
            ("2026-01-01", "2026-09-10", "2026-09-11"),
            ("2026-09-10", "2026-09-10", "2026-09-11"),
            ("2026-08-01", "2026-08-31", "2026-09-01"),
            ("2024-01-01", "2024-12-31", "2025-01-01"),
            ("2024-02-01", "2024-02-29", "2024-03-01"),
        ]
        for start, end, exclusive_end in periods:
            with self.subTest(start=start, end=end):
                queries = WidgetQueryBuilder(self.config).build(
                    datetime.datetime.fromisoformat(f"{end}T23:59:59+09:00"),
                    week_start_override=datetime.datetime.fromisoformat(f"{start}T00:00:00+09:00"),
                )
                created, resolved = queries.w3_created_vs_resolved()
                for field, query in (("created", created), ("resolved", resolved)):
                    self.assertIn(f'{field} >= "{start}" AND {field} < "{exclusive_end}"', query)
                    self.assertNotIn("<=", query)
                self.assertEqual(
                    f'{resolved} ORDER BY resolved DESC',
                    queries.w14_resolution_resolved(),
                )
                self.assertEqual(end, queries.date_end)
                self.assertEqual(end, queries.week_end.date().isoformat())

    def test_full_year_detail_queries_match_yearly_totals(self) -> None:
        queries = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2024, 12, 31),
            week_start_override=datetime.datetime(2024, 1, 1),
        )

        self.assertEqual(
            (queries.w1_yearly_created(), queries.w2_yearly_resolved()),
            queries.w3_created_vs_resolved(),
        )

    def test_resolution_type_filter_preserves_date_boundary_and_sort_order(self) -> None:
        query = self.queries.by_issue_type(self.queries.w14_resolution_resolved())["개선"]

        self.assertTrue(query.endswith(
            'AND resolved < "2026-08-19" AND issuetype = "개선" ORDER BY resolved DESC'
        ))

    def test_incomplete_issues_exclude_license_requests(self) -> None:
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'ORDER BY issuekey DESC',
            self.queries.w7_recent(),
        )

    def test_every_dashboard_query_excludes_license_requests(self) -> None:
        created, resolved = self.queries.w3_created_vs_resolved()
        dashboard_queries = [
            self.queries.w1_yearly_created(),
            self.queries.w2_yearly_resolved(),
            created,
            resolved,
            self.queries.w4_issue_review(),
            self.queries.w5_data_request(),
            self.queries.w6_result_pending(),
            self.queries.w7_recent(),
            self.queries.w8_monthly_created(2026, 8),
            self.queries.w9_monthly_resolved(2026, 8),
            self.queries.w10_w11_monthly_candidates(2026, 8),
            self.queries.w12_sla(),
            self.queries.w14_resolution_resolved(),
        ]

        for query in dashboard_queries:
            with self.subTest(query=query):
                self.assertNotIn("issuetype IN", query)
                self.assertIn('issuetype != "라이선스"', query)

    def test_type_breakdown_query_keeps_order_by_at_the_end(self) -> None:
        queries = self.queries.by_issue_type(self.queries.w7_recent())

        self.assertNotIn("라이선스", queries)
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'AND issuetype = "서비스 요청" ORDER BY issuekey DESC',
            queries["서비스 요청"],
        )

    def test_unlisted_types_query_keeps_order_by_at_the_end(self) -> None:
        query = self.queries.outside_issue_types(self.queries.w7_recent())

        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'AND issuetype NOT IN ("인시던트", "개선", "CVE", "서비스 요청") '
            'ORDER BY issuekey DESC',
            query,
        )

    def test_runtime_issue_types_replace_configured_fallback(self) -> None:
        queries = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2026, 8, 18),
            issue_types_override=["인시던트", "라이선스", "H/W 장애 요청", "승인된 서비스 요청"],
        )

        self.assertEqual(
            ("인시던트", "H/W 장애 요청", "승인된 서비스 요청"),
            queries.issue_types,
        )
        self.assertEqual(
            ["인시던트", "H/W 장애 요청", "승인된 서비스 요청"],
            list(queries.by_issue_type(queries.w1_yearly_created())),
        )

    def test_license_request_aliases_never_become_filter_options(self) -> None:
        queries = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2026, 8, 18),
            issue_types_override=[
                "인시던트",
                "라이선스",
                "라이센스",
                "라이선스 요청",
                "라이센스 요청",
            ],
        )

        self.assertEqual(("인시던트",), queries.issue_types)

    def test_widget_ids_follow_dashboard_render_order(self) -> None:
        self.assertEqual(
            [
                ("YEARLY_CREATED", "w1"),
                ("YEARLY_RESOLVED", "w2"),
                ("CREATED_VS_RESOLVED", "w3"),
                ("ISSUE_REVIEW", "w4"),
                ("DATA_REQUEST", "w5"),
                ("RESULT_PENDING", "w6"),
                ("RECENT_ISSUES", "w7"),
                ("MONTHLY_CREATED", "w8"),
                ("MONTHLY_RESOLVED", "w9"),
                ("SLA_INITIAL_RESPONSE", "w10"),
                ("SLA_RESOLUTION_MONTHLY", "w11"),
                ("SLA_MET_VS_VIOLATED", "w12"),
                ("SLA_DELAY_REASON", "w13"),
                ("AVG_RESOLUTION_TYPE", "w14"),
                ("REDEPLOYMENT_ANALYTICS", "w15"),
            ],
            [(widget_id.name, widget_id.value) for widget_id in WidgetId],
        )

    def test_redeployment_queries_use_the_report_year_and_field_ids(self) -> None:
        historical = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2024, 12, 31)
        )

        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND status = Closed AND resolution != Unresolved '
            'AND resolved >= "2024-01-01" AND resolved < "2025-01-01" '
            'AND type IN (\uac1c\uc120, \uc778\uc2dc\ub358\ud2b8, "\uc11c\ube44\uc2a4 \uc694\uccad")',
            historical.w15_redeployment_resolved(),
        )
        self.assertEqual(
            'project = TACEA AND issuetype != "라이선스" '
            'AND status = Closed AND cf[11819] = Y '
            'AND resolved >= "2024-01-01" AND resolved < "2025-01-01"',
            historical.w15_redeployment_issues(),
        )
        self.assertTrue(historical.w15_redeployment_analytics().endswith(
            'AND type IN (\uac1c\uc120, \uc778\uc2dc\ub358\ud2b8, "\uc11c\ube44\uc2a4 \uc694\uccad") '
            'ORDER BY cf[12421] DESC, resolved DESC'
        ))


class PeriodJira:
    def __init__(self):
        self.issues = [JiraIssue(
            key=key,
            summary=key,
            issue_type="개선",
            status="Closed",
            created=timestamp,
            resolved=timestamp,
        ) for key, timestamp in (
            ("BEFORE", "2025-12-31T23:59:59+09:00"),
            ("START", "2026-01-01T00:00:00+09:00"),
            ("END-MIDNIGHT", "2026-09-10T00:00:00+09:00"),
            ("END-LATE", "2026-09-10T23:59:59+09:00"),
            ("AFTER", "2026-09-11T00:00:00+09:00"),
        )]

    async def get_issues(self, jql, max_results, fields):
        comparisons = {">=": operator.ge, "<=": operator.le, "<": operator.lt}
        conditions = re.findall(r'(created|resolved) (>=|<=|<) "(\d{4}-\d{2}-\d{2})"', jql)
        result = self.issues
        for field, comparison, date in conditions:
            boundary = datetime.datetime.fromisoformat(f"{date}T00:00:00+09:00")
            result = [issue for issue in result if comparisons[comparison](
                datetime.datetime.fromisoformat(getattr(issue, field)), boundary,
            )]
        return result


class ReportPeriodCollectorsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.queries = WidgetQueryBuilder(QueryConfig("TACEA", ["개선"], [], [], 30, 2026)).build(
            datetime.datetime(2026, 9, 10),
            week_start_override=datetime.datetime(2026, 1, 1),
        )

    async def test_created_and_resolved_details_include_end_day_but_not_next_day(self) -> None:
        result = await CreatedVsResolvedCollector(PeriodJira(), self.queries).collect()

        self.assertEqual((3, 3), (result.data.created, result.data.resolved))
        for details in (result.data.created_details, result.data.resolved_details):
            self.assertEqual(["START", "END-MIDNIGHT", "END-LATE"], [issue.key for issue in details])

    async def test_resolution_statistics_include_end_day_but_not_next_day(self) -> None:
        result = await ResolutionCollector(PeriodJira(), self.queries, self.queries.week_end).collect()

        self.assertEqual(3, result.total)
        self.assertEqual(3, result.data.by_type["개선"].count)
        self.assertEqual(2, result.data.by_semester["h2"]["개선"].count)
