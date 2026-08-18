# backend/tests/test_query_builder.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig


class WidgetQueryBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        config = QueryConfig(
            project_key="TACEA",
            issue_types=["인시던트", "개선", "CVE", "서비스 요청"],
            active_statuses=["처리 중"],
            closed_statuses=["Closed"],
            sla_threshold_days=30,
            year_start=2026,
        )
        self.queries = WidgetQueryBuilder(config).build(
            datetime.datetime(2026, 8, 18)
        )

    def test_yearly_created_counts_every_issue_type_in_project(self) -> None:
        self.assertEqual(
            'project = TACEA AND created >= "2026-01-01"',
            self.queries.w1_yearly_created(),
        )

    def test_yearly_resolved_retains_dashboard_issue_type_scope(self) -> None:
        self.assertEqual(
            'project = TACEA AND issuetype IN (인시던트, 개선, CVE, "서비스 요청") '
            'AND resolved >= "2026-01-01"',
            self.queries.w2_yearly_resolved(),
        )
