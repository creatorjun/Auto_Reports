# backend/tests/test_recent_collector.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.ports.jira_port import JiraIssue
from src.application.widgets.recent_collector import RecentCollector
from src.domain.entities.widget_data import RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.factories.widget_collector_factory import WidgetCollectorFactory
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class RecentJira:
    def __init__(self, issue: JiraIssue) -> None:
        self.issue = issue
        self.requested_limits: list[int | None] = []

    async def get_issues_with_assignees(self, jql: str, max_results: int) -> list[JiraIssue]:
        self.requested_limits.append(max_results)
        return [self.issue]


def issue(**overrides: str) -> JiraIssue:
    return JiraIssue(
        key="TACEA-1",
        summary="담당자 구분 확인",
        issue_type="인시던트",
        status="할 일",
        created="2026-09-01T09:00:00.000+0900",
        **overrides,
    )


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
        self.now = datetime.datetime(2026, 9, 8, 23, 59, 59)
        self.queries = WidgetQueryBuilder(config).build(self.now)

    async def test_collects_tac_only_and_keeps_existing_assignee_precedence(self) -> None:
        jira = RecentJira(issue(
            reporter="보고자",
            recent_tac_assignee="TAC 담당자",
            tac_assignee="기존 담당자",
            qa_assignee="QA 담당자",
            assignee="일반 담당자",
        ))
        result = await RecentCollector(jira, self.queries, self.now).collect()

        detail = result.data.issue_details[0]
        self.assertEqual("TAC 담당자", detail.tac_assignee)
        self.assertEqual("기존 담당자", detail.tac_team)
        self.assertEqual("보고자", detail.reporter)
        self.assertEqual(7, detail.elapsed_days)
        self.assertEqual([None], jira.requested_limits)

    async def test_missing_tac_does_not_reuse_qa_or_general_assignee(self) -> None:
        for assignees, expected_assignee in [
            ({"tac_assignee": "기존 담당자"}, "기존 담당자"),
            ({"qa_assignee": "QA 담당자", "assignee": "일반 담당자"}, "QA 담당자"),
            ({"assignee": "일반 담당자"}, "일반 담당자"),
            ({}, "미지정"),
        ]:
            with self.subTest(assignees=assignees):
                result = await RecentCollector(
                    RecentJira(issue(**assignees)),
                    self.queries,
                    self.now,
                ).collect()

                detail = result.data.issue_details[0]
                self.assertEqual("미지정", detail.tac_assignee)
                self.assertEqual(expected_assignee, detail.tac_team)

    async def test_accepts_user_list_and_uses_first_named_tac_user(self) -> None:
        result = await RecentCollector(RecentJira(issue(
            recent_tac_assignee="tac-user",
            assignee="일반 담당자",
        )), self.queries, self.now).collect()

        detail = result.data.issue_details[0]
        self.assertEqual("tac-user", detail.tac_assignee)
        self.assertEqual("일반 담당자", detail.tac_team)

    async def test_new_tac_field_survives_saved_widget_round_trip(self) -> None:
        result = await RecentCollector(RecentJira(issue(
            recent_tac_assignee="TAC 담당자",
            assignee="일반 담당자",
        )), self.queries, self.now).collect()

        restored = deserialize_widget(WidgetId.RECENT_ISSUES, serialize_widget(result))

        self.assertIsInstance(restored.data, RecentIssueWidgetData)
        self.assertEqual("TAC 담당자", restored.data.issue_details[0].tac_assignee)
        self.assertEqual("일반 담당자", restored.data.issue_details[0].tac_team)

    async def test_legacy_snapshot_keeps_unknown_tac_separate_from_existing_assignee(self) -> None:
        result = await RecentCollector(RecentJira(issue(
            qa_assignee="QA 담당자",
        )), self.queries, self.now).collect()
        saved = serialize_widget(result)
        del saved["data"]["issue_details"][0]["tac_assignee"]

        restored = deserialize_widget(WidgetId.RECENT_ISSUES, saved)

        self.assertIsInstance(restored.data, RecentIssueWidgetData)
        self.assertIsNone(restored.data.issue_details[0].tac_assignee)
        self.assertEqual("QA 담당자", restored.data.issue_details[0].tac_team)

    async def test_factory_uses_the_typed_jira_boundary(self) -> None:
        jira = RecentJira(issue(recent_tac_assignee="설정한 TAC 담당자"))
        factory = WidgetCollectorFactory(jira)
        entry = next(
            entry
            for entry in factory.base_collectors(self.queries, self.now)
            if entry.widget_id == WidgetId.RECENT_ISSUES
        )

        result = await entry.collector.collect()

        self.assertEqual("설정한 TAC 담당자", result.data.issue_details[0].tac_assignee)
