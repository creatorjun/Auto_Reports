# backend/tests/test_widget_serializer.py
import unittest

from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    MonthlyEntry,
    RecentIssueDetail,
    RecentIssueWidgetData,
    ResolutionTypeEntry,
    ResolutionTypeWidgetData,
    SlaDelayIssueDetail,
    SlaDelayWidgetData,
    SlaMonthlyTypeStats,
    SlaMonthlyWidgetData,
    StageDurationIssue,
    TypeCountWidgetData,
)
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import deserialize_widget, serialize_widget


class WidgetSerializerTest(unittest.TestCase):
    def test_nested_widgets_round_trip_across_repeated_reads(self):
        fixtures = [
            (WidgetId.YEARLY_CREATED, TypeCountWidgetData(
                issue_types=["개선"], by_type={"개선": 2}, always_included=1,
                by_status_type={"Closed": {"개선": 2}}, status_breakdown_available=True,
            )),
            (WidgetId.RECENT_ISSUES, RecentIssueWidgetData([
                RecentIssueDetail("TACEA-1", "문의", "개선", "Closed", 9, "2026-01-01 09:00", 30),
            ])),
            (WidgetId.SLA_INITIAL_RESPONSE, SlaMonthlyWidgetData([
                MonthlyEntry("1월", 2026, 1, 50, 1, 2,
                    by_type={"개선": SlaMonthlyTypeStats(1, 2)},
                    by_status_type={"Closed": {"개선": SlaMonthlyTypeStats(1, 2)}},
                ),
            ])),
            (WidgetId.SLA_DELAY_REASON, SlaDelayWidgetData(
                by_status={"처리 중": 1},
                by_status_details={"처리 중": [SlaDelayIssueDetail("TACEA-1", "문의", "개선", "처리 중", "2026-01-01")]},
            )),
            (WidgetId.AVG_RESOLUTION_TYPE, ResolutionTypeWidgetData(
                by_type={"개선": ResolutionTypeEntry(1, 24, 1)},
                by_semester_status_type={"h1": {"Closed": {"개선": ResolutionTypeEntry(1, 24, 1)}}},
                stage_issues=[StageDurationIssue("TACEA-1", "개선", "Closed", "2026-01-02", {"처리 중": 24})],
            )),
            (WidgetId.AVG_RESOLUTION_TYPE, ResolutionTypeWidgetData(stage_issues=None)),
        ]
        for widget_id, data in fixtures:
            with self.subTest(widget_id=widget_id, data=data):
                expected = WidgetResult("위젯", 2, "project = TACEA", data)
                raw = serialize_widget(expected)
                for _ in range(3):
                    self.assertEqual(expected, deserialize_widget(widget_id, raw))

    def test_repeated_reads_do_not_share_mutable_data(self):
        raw = {
            "data": {"by_status_type": {"Closed": {"개선": 2}}, "issue_types": ["개선"]},
        }
        first = deserialize_widget(WidgetId.YEARLY_CREATED, raw)
        second = deserialize_widget(WidgetId.YEARLY_CREATED, raw)
        first.data.by_status_type["Closed"]["개선"] = 99
        first.data.issue_types.append("CVE")
        self.assertEqual(2, second.data.by_status_type["Closed"]["개선"])
        self.assertEqual(["개선"], second.data.issue_types)
        self.assertEqual(second, deserialize_widget(WidgetId.YEARLY_CREATED, raw))

    def test_legacy_defaults_and_malformed_data_remain_supported(self):
        raw = {"name": "위젯", "data": {"issue_details": [{
            "key": "TACEA-1", "summary": "문의", "type": "개선", "status": "Closed",
            "stage_index": 9, "created": "2026-01-01", "elapsed_days": 1,
        }]}}
        restored = deserialize_widget(WidgetId.RECENT_ISSUES, raw)
        self.assertEqual("미지정", restored.data.issue_details[0].reporter)
        self.assertIsNone(restored.data.issue_details[0].tac_assignee)
        self.assertIsNone(deserialize_widget("unknown", raw).data)
        raw["data"]["issue_details"] = None
        self.assertEqual([], deserialize_widget(WidgetId.RECENT_ISSUES, raw).data.issue_details)
        raw["data"]["issue_details"] = [{}]
        self.assertIsNone(deserialize_widget(WidgetId.RECENT_ISSUES, raw).data)
