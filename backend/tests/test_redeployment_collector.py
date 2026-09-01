# backend/tests/test_redeployment_collector.py
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.redeployment_collector import RedeploymentAnalyticsCollector
from src.domain.entities.widget_data import RedeploymentAnalyticsWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


def issue(
    key: str,
    issue_type: str,
    resolved: str,
    month: str,
    cause: str,
    assignee: str,
    partner_id: str,
) -> dict:
    return {
        "key": key,
        "fields": {
            "summary": f"{key} summary",
            "issuetype": {"name": issue_type},
            "priority": {"name": "Medium"},
            "resolutiondate": resolved,
            "assignee": {"displayName": assignee},
            "customfield_12421": {"value": month},
            "customfield_11885": {"value": cause},
            "customfield_10859": [
                {"workspaceId": "workspace", "objectId": partner_id}
            ],
        },
    }


class RedeploymentJira:
    def __init__(self) -> None:
        self.issues = [
            issue("TACEA-1", "\uac1c\uc120", "2024-01-15T10:00:00.000+0900", "2024-01", "\ubc30\ud3ec \uc2e4\uc218", "\ub2f4\ub2f9\uc790 A", "1"),
            issue("TACEA-2", "\uc778\uc2dc\ub358\ud2b8", "2024-02-20T10:00:00.000+0900", "2024-02", "\uc694\uad6c\uc0ac\ud56d \ubcc0\uacbd", "\ub2f4\ub2f9\uc790 B", "1"),
            issue("TACEA-3", "CVE", "2024-03-01T10:00:00.000+0900", "2024-03", "\uae30\ud0c0", "\ub2f4\ub2f9\uc790 C", "2"),
        ]

    async def get_issue_count(self, jql: str) -> int:
        return 3 if "\uc7ac\ubc30\ud3ec \uc5ec\ubd80" in jql else 10

    async def get_issues(self, jql: str, max_results: int | None, fields: str) -> list[dict]:
        if max_results is not None:
            raise AssertionError("redeployment collection must not be capped")
        return self.issues

    async def get_asset_object_labels(
        self,
        references: list[tuple[str, str]],
    ) -> dict[tuple[str, str], str]:
        return {
            ("workspace", "1"): "\ud30c\ud2b8\ub108 A",
            ("workspace", "2"): "\ud30c\ud2b8\ub108 B",
        }


class RedeploymentCollectorTest(unittest.IsolatedAsyncioTestCase):
    async def test_keeps_every_redeployment_issue_for_frontend_pagination(self) -> None:
        jira = RedeploymentJira()
        jira.issues.extend([
            issue(
                f"TACEA-{index}",
                "\uac1c\uc120",
                f"2026-08-{index + 10:02d}T10:00:00.000+0900",
                "2026-08",
                "\uae30\ud0c0",
                "\ub2f4\ub2f9\uc790 D",
                str(index),
            )
            for index in range(4, 8)
        ])
        config = QueryConfig(
            project_key="TACEA",
            issue_types=[],
            active_statuses=[],
            closed_statuses=[],
            sla_threshold_days=30,
            year_start=2026,
        )
        queries = WidgetQueryBuilder(config).build(datetime.datetime(2026, 12, 31))

        result = await RedeploymentAnalyticsCollector(jira, queries).collect()

        self.assertEqual(6, len(result.data.latest_issues))

    def test_maps_unassigned_partner_to_seculayer(self) -> None:
        empty_partner_issue = issue(
            "TACEA-4",
            "\uac1c\uc120",
            "2026-08-20T10:00:00.000+0900",
            "2026-08",
            "\uae30\ud0c0",
            "\ub2f4\ub2f9\uc790 D",
            "4",
        )
        empty_partner_issue["fields"]["customfield_10859"] = []
        unassigned_label_issue = issue(
            "TACEA-5",
            "\uac1c\uc120",
            "2026-08-21T10:00:00.000+0900",
            "2026-08",
            "\uae30\ud0c0",
            "\ub2f9\ub2f9\uc790 E",
            "5",
        )

        empty_detail = RedeploymentAnalyticsCollector._to_detail(empty_partner_issue, {})
        label_detail = RedeploymentAnalyticsCollector._to_detail(
            unassigned_label_issue,
            {("workspace", "5"): "\ubbf8\uc9c0\uc815"},
        )

        self.assertEqual(["\uc2dc\ud050\ub808\uc774\uc5b4"], empty_detail.partners)
        self.assertEqual(["\uc2dc\ud050\ub808\uc774\uc5b4"], label_detail.partners)

    async def test_collects_every_dashboard_view_with_year_fixed_jql(self) -> None:
        config = QueryConfig(
            project_key="TACEA",
            issue_types=[],
            active_statuses=[],
            closed_statuses=[],
            sla_threshold_days=30,
            year_start=2026,
        )
        queries = WidgetQueryBuilder(config).build(datetime.datetime(2024, 12, 31))
        result = await RedeploymentAnalyticsCollector(RedeploymentJira(), queries).collect()
        data = result.data

        self.assertIsInstance(data, RedeploymentAnalyticsWidgetData)
        self.assertEqual(10, data.resolved_total)
        self.assertEqual(3, data.redeployment_total)
        self.assertEqual(30.0, data.redeployment_rate)
        self.assertEqual(2, data.analytics_total)
        self.assertFalse(data.classification_complete)
        self.assertEqual(1, data.monthly[0].total)
        self.assertEqual(1, data.monthly[1].total)
        self.assertEqual({"\ubc30\ud3ec \uc2e4\uc218": 1, "\uc694\uad6c\uc0ac\ud56d \ubcc0\uacbd": 1}, data.by_cause)
        self.assertEqual({"\uac1c\uc120": 1, "\uc778\uc2dc\ub358\ud2b8": 1}, data.partner_matrix["\ud30c\ud2b8\ub108 A"])
        self.assertEqual({"CVE": 1}, data.partner_matrix["\ud30c\ud2b8\ub108 B"])
        self.assertEqual(["TACEA-2", "TACEA-1"], [item.key for item in data.latest_issues])
        self.assertIn('resolved >= "2024-01-01"', data.source_jqls["redeployed"])
        self.assertIn("cf[11819] = Y", data.source_jqls["redeployed"])

        restored = deserialize_widget(
            WidgetId.REDEPLOYMENT_ANALYTICS,
            serialize_widget(result),
        )
        self.assertIsInstance(restored.data, RedeploymentAnalyticsWidgetData)
        self.assertEqual("TACEA-2", restored.data.latest_issues[0].key)
