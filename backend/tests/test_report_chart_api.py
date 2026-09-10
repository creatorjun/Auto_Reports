# backend/tests/test_report_chart_api.py
import pathlib
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.application.errors import EntityNotFoundError
from src.domain.entities.report_chart import ReportChartIssue, ReportChartIssueResult
from src.presentation.api.deps import get_auth
from src.presentation.api.v1.deps import get_report_chart_issues_use_case
from src.presentation.api.v1.router import router


class RecordingChartUseCase:
    def __init__(self):
        self.selections = []
        self.error = None

    async def execute(self, report_id, selection):
        if self.error:
            raise self.error
        self.selections.append((report_id, selection))
        return ReportChartIssueResult(
            issues=[ReportChartIssue("T-1", "개별 이슈", "개선", sla_met=True)],
            snapshot_count=2, current_count=1, source_total=1, source_total_exact=True,
            collection_limit=500, truncated=False, queried_at="2026-09-10T00:00:00+09:00", snapshot_at="2024-12-31",
        )


class ReportChartApiTest(unittest.TestCase):
    def setUp(self):
        self.use_case = RecordingChartUseCase()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_report_chart_issues_use_case] = lambda: self.use_case
        app.dependency_overrides[get_auth] = lambda: SimpleNamespace(enabled=True, decode_access_token=lambda token: "tester")
        self.client = TestClient(app)
        self.endpoint = "/api/v1/reports/7/chart-issues"
        self.headers = {"Authorization": "Bearer test"}

    def tearDown(self):
        self.client.close()

    def test_existing_auth_protects_new_endpoint(self):
        response = self.client.get(self.endpoint, params={"chart": "sla_initial", "month": 1})
        self.assertEqual(401, response.status_code)
        self.assertEqual([], self.use_case.selections)

    def test_serialization_and_empty_type_filter_contract(self):
        response = self.client.get(self.endpoint, headers=self.headers, params={"chart": "sla_initial", "month": 1, "filter_types": "true", "sla_status": "met"})
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual((), self.use_case.selections[-1][1].selected_types)
        self.assertEqual("met", self.use_case.selections[-1][1].sla_status)
        self.assertEqual(True, response.json()["issues"][0]["sla_met"])
        self.assertEqual((2, 1), (response.json()["snapshot_count"], response.json()["current_count"]))
        self.client.get(self.endpoint, headers=self.headers, params={"chart": "sla_initial", "month": 1})
        self.assertIsNone(self.use_case.selections[-1][1].selected_types)

    def test_repeated_selected_types_and_invalid_parameters(self):
        response = self.client.get(self.endpoint, headers=self.headers, params=[("chart", "resolution_type"), ("filter_types", "true"), ("selected_types", "개선"), ("selected_types", "인시던트")])
        self.assertEqual(200, response.status_code)
        self.assertEqual(("개선", "인시던트"), self.use_case.selections[-1][1].selected_types)
        for params in ({"chart": "arbitrary_jql"}, {"chart": "sla_initial", "month": 13}, {"chart": "sla_initial"}, {"chart": "resolution_type", "partner": "A"}, {"chart": "sla_resolution", "month": 1, "sla_status": "wrong"}):
            with self.subTest(params=params):
                self.assertEqual(422, self.client.get(self.endpoint, headers=self.headers, params=params).status_code)

    def test_status_filter_supports_empty_repeated_and_disabled_selection(self):
        response = self.client.get(self.endpoint, headers=self.headers, params={
            "chart": "resolution_type", "filter_statuses": "true",
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual((), self.use_case.selections[-1][1].selected_statuses)
        response = self.client.get(self.endpoint, headers=self.headers, params=[
            ("chart", "resolution_type"), ("filter_statuses", "true"),
            ("selected_statuses", "Closed"), ("selected_statuses", "재오픈"),
        ])
        self.assertEqual(200, response.status_code)
        self.assertEqual(("Closed", "재오픈"), self.use_case.selections[-1][1].selected_statuses)
        response = self.client.get(self.endpoint, headers=self.headers, params={
            "chart": "resolution_type", "selected_statuses": "Closed",
        })
        self.assertEqual(200, response.status_code)
        self.assertIsNone(self.use_case.selections[-1][1].selected_statuses)
        response = self.client.get(self.endpoint, headers=self.headers, params={
            "chart": "resolution_type", "filter_statuses": "true", "selected_statuses": " ",
        })
        self.assertEqual(422, response.status_code)

    def test_upstream_failures_return_safe_error(self):
        self.use_case.error = RuntimeError("private upstream details")
        response = self.client.get(self.endpoint, headers=self.headers, params={"chart": "resolution_type"})
        self.assertEqual(502, response.status_code)
        self.assertNotIn("private", response.text)
