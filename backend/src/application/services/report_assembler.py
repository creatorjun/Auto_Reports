# backend/src/application/services/report_assembler.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.widgets.count_collector import (
    BreakdownCollector,
    SimpleCountCollector,
    SimpleWithDetailsCollector,
    SlaMetVsViolatedCollector,
)
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.monthly_collector import MonthlyCollector
from src.application.widgets.overdue_collector import OverdueCollector
from src.application.widgets.recent_collector import RecentCollector
from src.application.widgets.resolution_collector import ResolutionCollector
from src.application.widgets.sla_delay_collector import SlaDelayCollector
from src.domain.entities.report import NewReport
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class ReportAssembler:
    def __init__(
        self,
        jira: JiraPort,
        query_builder: WidgetQueryBuilder,
        sla_threshold_days: int,
        sla_initial_response_field_id: str,
        sla_resolution_field_id: str,
    ):
        self._jira = jira
        self._qb = query_builder
        self._sla_threshold_days = sla_threshold_days
        self._sla_initial_response_field_id = sla_initial_response_field_id
        self._sla_resolution_field_id = sla_resolution_field_id

    async def collect(self, now: datetime) -> NewReport:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        q = self._qb.build(now)
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        collectors = [
            (WidgetId.OVERDUE_ISSUES, OverdueCollector(self._jira, q, self._sla_threshold_days)),
            (WidgetId.ISSUE_REVIEW, SimpleWithDetailsCollector(self._jira, "이슈 리뷰 중", q.w2_issue_review())),
            (WidgetId.DATA_REQUEST, SimpleWithDetailsCollector(self._jira, "자료 요청 중", q.w3_data_request())),
            (WidgetId.LAB_UNASSIGNED, SimpleCountCollector(self._jira, "연구소 대기(담당자 미지정)", q.w4_lab_unassigned())),
            (WidgetId.SLA_DELAY_BY_TYPE, BreakdownCollector(self._jira, "유형별 SLA 지연", q.w5_by_type())),
            (WidgetId.SLA_DELAY_BY_STATUS, BreakdownCollector(self._jira, "상태별 SLA 지연", q.w6_by_status())),
            (WidgetId.SLA_DELAY_REASON, SlaDelayCollector(self._jira, q, self._sla_threshold_days)),
            (WidgetId.YEARLY_CREATED, SimpleCountCollector(self._jira, f"{now.year}년 누적 생성", q.w8_yearly_created())),
            (WidgetId.YEARLY_RESOLVED, SimpleCountCollector(self._jira, f"{now.year}년 누적 해결", q.w9_yearly_resolved())),
            (WidgetId.AVG_RESOLUTION_TYPE, ResolutionCollector(self._jira, q)),
            (WidgetId.RESOLUTION_REPORT, RecentCollector(self._jira, q)),
            (
                WidgetId.SLA_MET_VS_VIOLATED,
                SlaMetVsViolatedCollector(
                    self._jira, q,
                    self._sla_initial_response_field_id,
                    self._sla_resolution_field_id,
                ),
            ),
            (WidgetId.RESULT_PENDING, SimpleWithDetailsCollector(self._jira, "결과 대기 중", q.w13_result_pending())),
            (WidgetId.CREATED_VS_RESOLVED, CreatedVsResolvedCollector(self._jira, q)),
        ]

        monthly_collector = MonthlyCollector(
            self._jira, q, now,
            self._sla_initial_response_field_id,
            self._sla_resolution_field_id,
        )

        base_results = await asyncio.gather(*[c.collect() for _, c in collectors])
        w15_result, w16_result = await monthly_collector.collect()

        widgets = {widget_id: result for (widget_id, _), result in zip(collectors, base_results)}
        widgets[WidgetId.SLA_INITIAL_RESPONSE] = w15_result
        widgets[WidgetId.SLA_RESOLUTION_MONTHLY] = w16_result

        logger.info("데이터 수집 완료 ✅")
        return NewReport(
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets,
        )
