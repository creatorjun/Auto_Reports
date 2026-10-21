# backend/tests/test_ai_analysis_persistence.py
import dataclasses
import unittest
from copy import deepcopy
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import JSON, Column, Date, DateTime, Integer, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.orm import Session

from src.domain.entities.report import NewReport
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import TypeCountWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.persistence.widget_serializer import serialize_widget
from src.presentation.mappers.report_mapper import ReportMapper


LEGACY_ANALYSIS = {
    "summary": "저장된 보고서 요약",
    "risks": ["자료 요청 단계 확인 필요"],
    "recommendations": ["기록된 체류시간 검토"],
    "sentiment": "warning",
}
CURRENT_ANALYSIS = {
    **LEGACY_ANALYSIS,
    "bottlenecks": ["해결 이력의 자료 요청 단계 체류시간 확인"],
    "provider": "rovo_automation",
    "analyzed_at": "2026-10-21T02:03:00+00:00",
    "is_stale": False,
}


def report_fixture() -> NewReport:
    return NewReport(
        week_start=date(2026, 10, 1),
        week_end=date(2026, 10, 31),
        report_date="2026-10-31T23:59:59+09:00",
        widgets={WidgetId.YEARLY_CREATED: WidgetResult(
            name="연간 생성", total=7, jql="project = TACEA",
            data=TypeCountWidgetData(issue_types=["개선"], by_type={"개선": 7}),
        )},
    )


class AiAnalysisPersistenceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        metadata = MetaData()
        self.table = Table(
            "reports", metadata,
            Column("id", Integer, primary_key=True),
            Column("week_start", Date, nullable=False),
            Column("week_end", Date, nullable=False),
            Column("report_date", String, nullable=False),
            Column("widgets", JSON, nullable=False),
            Column("ai_analysis", JSON, nullable=True),
            Column("scope", String, nullable=False),
            Column("report_year", Integer, nullable=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        bridge = SimpleNamespace(
            get_bind=self.session.get_bind,
            execute=AsyncMock(side_effect=self.session.execute),
            flush=AsyncMock(side_effect=self.session.flush),
        )
        self.repository = ReportRepositoryImpl(bridge)
        self.next_id = 1

    def seed(self, analysis: dict | None) -> int:
        report = report_fixture()
        report_id = self.next_id
        self.next_id += 1
        self.session.execute(insert(self.table), {
            "id": report_id,
            "week_start": report.week_start,
            "week_end": report.week_end,
            "report_date": report.report_date,
            "widgets": {key: serialize_widget(widget) for key, widget in report.widgets.items()},
            "ai_analysis": deepcopy(analysis),
            "scope": "standard",
            "report_year": None,
            "created_at": datetime(2026, 10, 21, 2, 3, tzinfo=timezone.utc),
        })
        self.session.commit()
        return report_id

    def stored_analysis(self, report_id: int) -> dict | None:
        return self.session.execute(select(self.table.c.ai_analysis).where(self.table.c.id == report_id)).scalar_one()

    async def update_and_reload(self, report_id: int, report: NewReport):
        result = await self.repository.update_widgets(report_id, report)
        self.session.commit()
        self.session.expire_all()
        reloaded = await self.repository.find_by_id(report_id)
        self.assertEqual(result, reloaded)
        return reloaded

    async def test_legacy_json_loads_and_maps_without_new_fields_or_rewriting_history(self):
        report_id = self.seed(LEGACY_ANALYSIS)
        report = await self.repository.find_by_id(report_id)
        mapped = ReportMapper.to_detail(report).model_dump(mode="json")["ai_analysis"]
        self.assertEqual({
            **LEGACY_ANALYSIS,
            "bottlenecks": [], "provider": None, "analyzed_at": None, "is_stale": False,
        }, mapped)
        self.assertEqual("warning", (await self.repository.find_summaries())[0].sentiment)
        self.assertEqual(LEGACY_ANALYSIS, self.stored_analysis(report_id))

    async def test_unchanged_widgets_and_period_preserve_fresh_analysis_and_its_timestamp(self):
        for analysis in (LEGACY_ANALYSIS, CURRENT_ANALYSIS):
            with self.subTest(legacy="is_stale" not in analysis):
                report_id = self.seed(analysis)
                report = await self.update_and_reload(report_id, dataclasses.replace(
                    report_fixture(), report_date="2026-10-31T23:59:00+09:00",
                ))
                self.assertFalse(report.ai_analysis.is_stale)
                self.assertEqual(analysis, self.stored_analysis(report_id))
                self.assertEqual(analysis.get("analyzed_at"), report.ai_analysis.analyzed_at)

    async def test_nested_widget_data_change_marks_analysis_stale_without_replacing_its_content(self):
        report_id = self.seed(CURRENT_ANALYSIS)
        updated = report_fixture()
        updated.widgets[WidgetId.YEARLY_CREATED].data.by_type = {"개선": 5, "서비스 요청": 2}
        report = await self.update_and_reload(report_id, updated)
        self.assertEqual(7, report.widgets[WidgetId.YEARLY_CREATED].total)
        self.assertEqual({**CURRENT_ANALYSIS, "is_stale": True}, self.stored_analysis(report_id))
        self.assertEqual({**CURRENT_ANALYSIS, "is_stale": True}, ReportMapper.to_detail(report).model_dump(mode="json")["ai_analysis"])

    async def test_either_saved_period_boundary_change_marks_analysis_stale(self):
        for changes in ({"week_start": date(2026, 10, 2)}, {"week_end": date(2026, 10, 30)}):
            with self.subTest(changes=changes):
                report_id = self.seed(CURRENT_ANALYSIS)
                updated = dataclasses.replace(report_fixture(), **changes)
                report = await self.update_and_reload(report_id, updated)
                self.assertEqual(updated.week_start, report.week_start)
                self.assertEqual(updated.week_end, report.week_end)
                self.assertEqual({**CURRENT_ANALYSIS, "is_stale": True}, self.stored_analysis(report_id))

    async def test_already_stale_analysis_stays_stale_after_an_unchanged_refresh(self):
        stale = {**CURRENT_ANALYSIS, "is_stale": True}
        report_id = self.seed(stale)
        report = await self.update_and_reload(report_id, report_fixture())
        self.assertTrue(report.ai_analysis.is_stale)
        self.assertEqual(stale, self.stored_analysis(report_id))

    async def test_changed_legacy_report_adds_only_stale_metadata_to_saved_analysis(self):
        report_id = self.seed(LEGACY_ANALYSIS)
        updated = dataclasses.replace(report_fixture(), week_end=date(2026, 10, 30))
        report = await self.update_and_reload(report_id, updated)
        self.assertTrue(report.ai_analysis.is_stale)
        self.assertIsNone(report.ai_analysis.analyzed_at)
        self.assertEqual({**LEGACY_ANALYSIS, "is_stale": True}, self.stored_analysis(report_id))

    async def test_report_without_analysis_stays_without_analysis_when_its_data_changes(self):
        report_id = self.seed(None)
        updated = dataclasses.replace(report_fixture(), week_end=date(2026, 10, 30))
        report = await self.update_and_reload(report_id, updated)
        self.assertIsNone(report.ai_analysis)
        self.assertIsNone(self.stored_analysis(report_id))
        self.assertIsNone(ReportMapper.to_detail(report).ai_analysis)
