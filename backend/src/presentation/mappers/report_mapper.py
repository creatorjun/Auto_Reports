# backend/src/presentation/mappers/report_mapper.py
import dataclasses

from src.domain.entities.report import Report
from src.domain.value_objects.widget_id import WidgetId
from src.presentation.schemas.report_schema import (
    AiAnalysisSchema,
    ReportDetailSchema,
    ReportSummarySchema,
    WidgetResultSchema,
)


class ReportMapper:
    @staticmethod
    def to_summary(report: Report) -> ReportSummarySchema:
        return ReportSummarySchema(
            id=report.id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            created_at=report.created_at,
            sentiment=report.ai_analysis.sentiment if report.ai_analysis else None,
            scope=report.scope.value,
            report_year=report.report_year,
        )

    @staticmethod
    def to_detail(report: Report) -> ReportDetailSchema:
        ordered_ids = [widget_id for widget_id in WidgetId if widget_id in report.widgets]
        ordered_ids.extend(key for key in report.widgets if key not in ordered_ids)
        widgets = {
            widget_id: WidgetResultSchema(
                name=report.widgets[widget_id].name,
                total=report.widgets[widget_id].total,
                jql=report.widgets[widget_id].jql,
                data=(
                    dataclasses.asdict(report.widgets[widget_id].data)
                    if report.widgets[widget_id].data is not None
                    else None
                ),
            )
            for widget_id in ordered_ids
        }
        ai = None
        if report.ai_analysis:
            ai = AiAnalysisSchema(
                summary=report.ai_analysis.summary,
                risks=report.ai_analysis.risks,
                recommendations=report.ai_analysis.recommendations,
                sentiment=report.ai_analysis.sentiment,
            )
        return ReportDetailSchema(
            id=report.id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            created_at=report.created_at,
            widgets=widgets,
            ai_analysis=ai,
            scope=report.scope.value,
            report_year=report.report_year,
        )
