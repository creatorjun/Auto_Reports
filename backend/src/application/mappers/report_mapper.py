# backend/src/application/mappers/report_mapper.py
import dataclasses

from src.domain.entities.report import Report
from src.presentation.schemas.report_schema import (
    AiAnalysisSchema,
    ReportDetailSchema,
    ReportSummarySchema,
    WidgetResultSchema,
)


class ReportMapper:
    """Domain Report → Presentation Schema 전담 매퍼.

    Presentation 레이어가 Domain 내부를 직접 파사리하지 않도록
    모든 변환 로직을 이 클래스에 집중시킵니다.
    """

    @staticmethod
    def to_summary(report: Report) -> ReportSummarySchema:
        return ReportSummarySchema(
            id=report.id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            created_at=report.created_at,
            sentiment=report.ai_analysis.sentiment if report.ai_analysis else None,
        )

    @staticmethod
    def to_detail(report: Report) -> ReportDetailSchema:
        widgets = {
            k: WidgetResultSchema(
                name=v.name,
                total=v.total,
                jql=v.jql,
                data=dataclasses.asdict(v.data) if v.data is not None else None,
            )
            for k, v in report.widgets.items()
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
        )
