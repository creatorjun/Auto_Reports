# backend/src/application/services/report_assembler.py
import asyncio
import logging
from datetime import datetime

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.widgets.count_collector import (
    SimpleCountCollector,
    SimpleWithDetailsCollector,
    SlaMetVsViolatedCollector,
)
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.monthly_collector import MonthlyCollector
from src.application.widgets.monthly_count_collector import MonthlyCountCollector
from src.application.widgets.recent_collector import RecentCollector
from src.application.widgets.resolution_collector import ResolutionCollector
from src.application.widgets.sla_delay_collector import SlaDelayCollector
from src.domain.entities.report import NewReport
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId
from src.shared.constants import KST

logger = logging.getLogger(__name__)


class ReportAssembler:
    def __init__(
        self,
        jira: JiraPort,
        query_builder: WidgetQueryBuilder,
        sla_threshold_days: int,
        sla_initial_response_field_id: str,
        sla_resolution_field_id: str,
        jira_tac_assignee_field_id: str,
        jira_qa_assignee_field_id: str,
    ):
        self._jira = jira
        self._qb = query_builder
        self._sla_threshold_days = sla_threshold_days
        self._sla_initial_response_field_id = sla_initial_response_field_id
        self._sla_resolution_field_id = sla_resolution_field_id
        self._jira_tac_assignee_field_id = jira_tac_assignee_field_id
        self._jira_qa_assignee_field_id = jira_qa_assignee_field_id

    async def collect(
        self,
        now: datetime,
        week_start_override: datetime | None = None,
    ) -> NewReport:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        q = self._qb.build(now, week_start_override=week_start_override)
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        collectors = [
            (WidgetId.YEARLY_CREATED,      SimpleCountCollector(self._jira, f"{now.year}년 누적 생성", q.w1_yearly_created())),
            (WidgetId.YEARLY_RESOLVED,     SimpleCountCollector(self._jira, f"{now.year}년 누적 해결", q.w2_yearly_resolved())),
            (WidgetId.CREATED_VS_RESOLVED, CreatedVsResolvedCollector(self._jira, q)),
            (WidgetId.ISSUE_REVIEW,        SimpleWithDetailsCollector(self._jira, "이슈 리뷰 중", q.w4_issue_review())),
            (WidgetId.DATA_REQUEST,        SimpleWithDetailsCollector(self._jira, "자료 요청 중", q.w5_data_request())),
            (WidgetId.RESULT_PENDING,      SimpleWithDetailsCollector(self._jira, "결과 대기 중", q.w6_result_pending())),
            (
                WidgetId.SLA_MET_VS_VIOLATED,
                SlaMetVsViolatedCollector(
                    self._jira, q,
                    self._sla_initial_response_field_id,
                    self._sla_resolution_field_id,
                ),
            ),
            (
                WidgetId.SLA_DELAY_REASON,
                SlaDelayCollector(
                    self._jira, q,
                    self._sla_initial_response_field_id,
                    self._sla_resolution_field_id,
                ),
            ),
            (WidgetId.AVG_RESOLUTION_TYPE, ResolutionCollector(self._jira, q)),
            (
                WidgetId.RECENT_ISSUES,
                RecentCollector(
                    self._jira, q,
                    self._jira_tac_assignee_field_id,
                    self._jira_qa_assignee_field_id,
                ),
            ),
        ]

        monthly_collector = MonthlyCollector(
            self._jira, q, now,
            self._sla_initial_response_field_id,
            self._sla_resolution_field_id,
        )
        monthly_count_collector = MonthlyCountCollector(self._jira, q, now)

        base_task    = asyncio.gather(*[c.collect() for _, c in collectors])
        monthly_task = monthly_collector.collect()
        monthly_count_task = monthly_count_collector.collect()

        base_results, (w7_result, w8_result), (w13_result, w14_result) = await asyncio.gather(
            base_task,
            monthly_task,
            monthly_count_task,
        )

        widgets = {widget_id: result for (widget_id, _), result in zip(collectors, base_results)}
        widgets[WidgetId.SLA_INITIAL_RESPONSE]   = w7_result
        widgets[WidgetId.SLA_RESOLUTION_MONTHLY] = w8_result
        widgets[WidgetId.MONTHLY_CREATED]        = w13_result
        widgets[WidgetId.MONTHLY_RESOLVED]       = w14_result

        logger.info("데이터 수집 완료 ✅")
        return NewReport(
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets,
        )
