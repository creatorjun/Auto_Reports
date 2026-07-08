# backend/tests/unit/domain/test_report_entity.py
"""
Report 엔티티 불변성 검증.

NewReport는 id가 없는 저장 전 상태를, Report는 DB 저장 후
식별자를 가진 상태를 표현한다. 둘 다 frozen=True이므로
외부에서 서 필드를 직접 변경할 수 없어야 한다.
"""
import dataclasses
import datetime

import pytest

from src.domain.entities.report import NewReport, Report


class TestNewReport:
    def test_frozen_raises_on_setattr(self, sample_new_report: NewReport):
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sample_new_report.report_date = "변경되면 안 됨"  # type: ignore

    def test_has_no_id_field(self, sample_new_report: NewReport):
        assert not hasattr(sample_new_report, "id")

    def test_default_widgets_is_empty_dict(self):
        r = NewReport(
            week_start=datetime.date(2026, 1, 1),
            week_end=datetime.date(2026, 1, 7),
            report_date="2026-01-07 23:00",
        )
        assert r.widgets == {}


class TestReport:
    def test_inherits_new_report_fields(self, sample_report: Report):
        assert sample_report.week_start == datetime.date(2026, 7, 1)
        assert sample_report.week_end == datetime.date(2026, 7, 7)

    def test_has_valid_id(self, sample_report: Report):
        assert sample_report.id == 42

    def test_frozen_raises_on_setattr(self, sample_report: Report):
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sample_report.id = 999  # type: ignore

    def test_replace_produces_new_instance(self, sample_report: Report):
        updated = dataclasses.replace(sample_report, id=99)
        assert updated.id == 99
        assert sample_report.id == 42  # 원본 불변
