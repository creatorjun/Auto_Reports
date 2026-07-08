# backend/tests/unit/domain/test_widget_serializer.py
"""
WidgetSerializer 직렬화/역직렬화 화람테스트.

serialize → deserialize 라운드트립으로 데이터 손실 없이
복원되는지 검증한다.
"""
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import SimpleIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.widget_serializer import (
    deserialize_widget,
    serialize_widget,
)


class TestWidgetSerializerRoundtrip:
    def _make_widget(self) -> WidgetResult:
        return WidgetResult(
            name="이슈 리뷰 중",
            total=5,
            jql="project = TEST",
            data=SimpleIssueWidgetData(count=5, issue_keys=["TEST-1", "TEST-2"]),
        )

    def test_serialize_produces_dict(self):
        widget = self._make_widget()
        raw = serialize_widget(widget)
        assert isinstance(raw, dict)
        assert raw["name"] == "이슈 리뷰 중"
        assert raw["total"] == 5
        assert raw["data"]["count"] == 5

    def test_deserialize_restores_widget(self):
        widget = self._make_widget()
        raw = serialize_widget(widget)
        restored = deserialize_widget(WidgetId.ISSUE_REVIEW, raw)
        assert restored.name == widget.name
        assert restored.total == widget.total
        assert isinstance(restored.data, SimpleIssueWidgetData)
        assert restored.data.count == 5

    def test_deserialize_unknown_widget_id_returns_none_data(self):
        raw = {"name": "unknown", "total": 0, "jql": "", "data": {"foo": "bar"}}
        restored = deserialize_widget("unknown_widget", raw)
        assert restored.data is None

    def test_serialize_none_data_widget(self):
        widget = WidgetResult(name="빈 위젯", total=0, jql="", data=None)
        raw = serialize_widget(widget)
        assert raw["data"] is None
        restored = deserialize_widget(WidgetId.ISSUE_REVIEW, raw)
        assert restored.data is None
