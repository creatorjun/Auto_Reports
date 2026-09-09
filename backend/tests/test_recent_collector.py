# backend/tests/test_recent_collector.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.recent_collector import RecentCollector
from src.domain.entities.widget_data import RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class RecentJira:
    def __init__(self, fields: dict) -> None:
        self.fields = fields
        self.requested_extra_fields: list[str] = []
        self.requested_limits: list[int | None] = []

    async def get_issues_with_assignees(self, jql: str, max_results: int, extra_fields: str = "") -> list[dict]:
        self.requested_extra_fields.append(extra_fields)
        self.requested_limits.append(max_results)
        return [{
            "key": "TACEA-1",
            "fields": {
                "summary": "담당자 구분 확인",
                "issuetype": {"name": "인시던트"},
                "status": {"name": "할 일"},
                "created": "2026-09-01T09:00:00.000+0900",
                **self.fields,
            },
        }]


class RecentCollectorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = QueryConfig(
            project_key="TACEA",
            issue_types=[],
            active_statuses=["할 일"],
            closed_statuses=[],
            sla_threshold_days=30,
            year_start=2026,
        )
        self.queries = WidgetQueryBuilder(config).build(datetime.datetime(2026, 9, 8))

    async def test_collects_tac_only_and_keeps_existing_assignee_precedence(self) -> None:
        jira = RecentJira({
            "reporter": {"displayName": "보고자"},
            "customfield_12522": {"displayName": "TAC 담당자"},
            "_tac_assignee": {"displayName": "기존 담당자"},
            "_qa_assignee": {"displayName": "QA 담당자"},
            "assignee": {"displayName": "일반 담당자"},
        })
        result = await RecentCollector(
            jira, self.queries, tac_assignee_field_id="customfield_12522",
        ).collect()

        detail = result.data.issue_details[0]
        self.assertEqual("TAC 담당자", detail.tac_assignee)
        self.assertEqual("기존 담당자", detail.tac_team)
        self.assertEqual("보고자", detail.reporter)
        self.assertEqual(["customfield_12522"], jira.requested_extra_fields)
        self.assertEqual([None], jira.requested_limits)

    async def test_missing_tac_does_not_reuse_qa_or_general_assignee(self) -> None:
        for fields, expected_assignee in [
            ({"_tac_assignee": {"displayName": "기존 담당자"}}, "기존 담당자"),
            ({"_qa_assignee": {"displayName": "QA 담당자"}, "assignee": {"displayName": "일반 담당자"}}, "QA 담당자"),
            ({"assignee": {"displayName": "일반 담당자"}}, "일반 담당자"),
            ({}, "미지정"),
        ]:
            with self.subTest(fields=fields):
                result = await RecentCollector(
                    RecentJira(fields), self.queries, tac_assignee_field_id="customfield_12522",
                ).collect()

                detail = result.data.issue_details[0]
                self.assertEqual("미지정", detail.tac_assignee)
                self.assertEqual(expected_assignee, detail.tac_team)

    async def test_accepts_user_list_and_uses_first_named_tac_user(self) -> None:
        result = await RecentCollector(RecentJira({
            "customfield_12522": [None, {}, {"name": "tac-user"}, {"displayName": "다음 담당자"}],
            "assignee": {"displayName": "일반 담당자"},
        }), self.queries, tac_assignee_field_id="customfield_12522").collect()

        detail = result.data.issue_details[0]
        self.assertEqual("tac-user", detail.tac_assignee)
        self.assertEqual("일반 담당자", detail.tac_team)

    async def test_new_tac_field_survives_saved_widget_round_trip(self) -> None:
        result = await RecentCollector(RecentJira({
            "customfield_12522": {"displayName": "TAC 담당자"},
            "assignee": {"displayName": "일반 담당자"},
        }), self.queries, tac_assignee_field_id="customfield_12522").collect()

        restored = deserialize_widget(WidgetId.RECENT_ISSUES, serialize_widget(result))

        self.assertIsInstance(restored.data, RecentIssueWidgetData)
        self.assertEqual("TAC 담당자", restored.data.issue_details[0].tac_assignee)
        self.assertEqual("일반 담당자", restored.data.issue_details[0].tac_team)

    async def test_legacy_snapshot_keeps_unknown_tac_separate_from_existing_assignee(self) -> None:
        result = await RecentCollector(RecentJira({
            "_qa_assignee": {"displayName": "QA 담당자"},
        }), self.queries, tac_assignee_field_id="customfield_12522").collect()
        saved = serialize_widget(result)
        del saved["data"]["issue_details"][0]["tac_assignee"]

        restored = deserialize_widget(WidgetId.RECENT_ISSUES, saved)

        self.assertIsInstance(restored.data, RecentIssueWidgetData)
        self.assertIsNone(restored.data.issue_details[0].tac_assignee)
        self.assertEqual("QA 담당자", restored.data.issue_details[0].tac_team)

    async def test_factory_injects_configurable_tac_field_into_recent_collector(self) -> None:
        jira = RecentJira({
            "customfield_90000": {"displayName": "설정한 TAC 담당자"},
            "customfield_12522": {"displayName": "다른 필드 담당자"},
        })
        factory = WidgetCollectorFactory(jira, recent_tac_assignee_field_id="customfield_90000")
        entry = next(
            entry
            for entry in factory.base_collectors(self.queries, datetime.datetime(2026, 9, 8))
            if entry.widget_id == WidgetId.RECENT_ISSUES
        )

        result = await entry.collector.collect()

        self.assertEqual("설정한 TAC 담당자", result.data.issue_details[0].tac_assignee)
        self.assertEqual(["customfield_90000"], jira.requested_extra_fields)
