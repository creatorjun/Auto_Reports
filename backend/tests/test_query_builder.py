# backend/tests/test_query_builder.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
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

    def test_yearly_created_uses_every_project_request_type(self) -> None:
        self.assertEqual(
            'project = TACEA AND created >= "2026-01-01" AND created < "2027-01-01"',
            self.queries.w1_yearly_created(),
        )

    def test_yearly_resolved_uses_every_project_request_type(self) -> None:
        self.assertEqual(
            'project = TACEA AND resolved >= "2026-01-01" AND resolved < "2027-01-01"',
            self.queries.w2_yearly_resolved(),
        )

    def test_historical_report_uses_the_requested_year(self) -> None:
        historical = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2024, 12, 31)
        )

        self.assertEqual(
            'project = TACEA AND created >= "2024-01-01" AND created < "2025-01-01"',
            historical.w1_yearly_created(),
        )
        self.assertEqual(
            'project = TACEA AND resolved >= "2024-01-01" AND resolved < "2025-01-01"',
            historical.w2_yearly_resolved(),
        )

    def test_incomplete_issues_use_every_project_request_type(self) -> None:
        self.assertEqual(
            'project = TACEA AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'ORDER BY issuekey DESC',
            self.queries.w7_recent(),
        )

    def test_every_dashboard_query_uses_project_wide_issue_types(self) -> None:
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
                self.assertNotIn("issuetype !=", query)

    def test_type_breakdown_query_keeps_order_by_at_the_end(self) -> None:
        queries = self.queries.by_issue_type(self.queries.w7_recent())

        self.assertEqual(
            'project = TACEA AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'AND issuetype = "라이선스" ORDER BY issuekey DESC',
            queries["라이선스"],
        )

    def test_unlisted_types_query_keeps_order_by_at_the_end(self) -> None:
        query = self.queries.outside_issue_types(self.queries.w7_recent())

        self.assertEqual(
            'project = TACEA AND status NOT IN ("Closed", "반려됨", "중복 이슈", "취소됨") '
            'AND issuetype NOT IN ("인시던트", "개선", "CVE", "서비스 요청", "라이선스") '
            'ORDER BY issuekey DESC',
            query,
        )

    def test_runtime_issue_types_replace_configured_fallback(self) -> None:
        queries = WidgetQueryBuilder(self.config).build(
            datetime.datetime(2026, 8, 18),
            issue_types_override=["인시던트", "H/W 장애 요청", "승인된 서비스 요청"],
        )

        self.assertEqual(
            ("인시던트", "H/W 장애 요청", "승인된 서비스 요청"),
            queries.issue_types,
        )
        self.assertEqual(
            ["인시던트", "H/W 장애 요청", "승인된 서비스 요청"],
            list(queries.by_issue_type(queries.w1_yearly_created())),
        )

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
            ],
            [(widget_id.name, widget_id.value) for widget_id in WidgetId],
        )
