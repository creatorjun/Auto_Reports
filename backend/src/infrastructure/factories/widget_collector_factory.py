# backend/src/infrastructure/factories/widget_collector_factory.py
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.collector_factory import CollectorEntry
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
from src.application.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId


class WidgetCollectorFactory:
    def __init__(self, jira: JiraPort):
        self._jira = jira

    def base_collectors(self, q: ResolvedQueries, now: datetime) -> list[CollectorEntry]:
        jira = self._jira
        return [
            CollectorEntry(WidgetId.YEARLY_CREATED,      SimpleCountCollector(jira, f"{now.year}\ub144 \ub204\uc801 \uc0dd\uc131", q.w1_yearly_created())),
            CollectorEntry(WidgetId.YEARLY_RESOLVED,     SimpleCountCollector(jira, f"{now.year}\ub144 \ub204\uc801 \ud574\uacb0", q.w2_yearly_resolved())),
            CollectorEntry(WidgetId.CREATED_VS_RESOLVED, CreatedVsResolvedCollector(jira, q)),
            CollectorEntry(WidgetId.ISSUE_REVIEW,        SimpleWithDetailsCollector(jira, "\uc774\uc288 \ub9ac\ubdf0 \uc911", q.w4_issue_review())),
            CollectorEntry(WidgetId.DATA_REQUEST,        SimpleWithDetailsCollector(jira, "\uc790\ub8cc \uc694\uccad \uc911", q.w5_data_request())),
            CollectorEntry(WidgetId.RESULT_PENDING,      SimpleWithDetailsCollector(jira, "\uacb0\uacfc \ub300\uae30 \uc911", q.w6_result_pending())),
            CollectorEntry(WidgetId.PROCESSING,          SimpleWithDetailsCollector(jira, "\ucc98\ub9ac \uc911", q.w15_processing())),
            CollectorEntry(WidgetId.SLA_MET_VS_VIOLATED, SlaMetVsViolatedCollector(jira, q)),
            CollectorEntry(WidgetId.SLA_DELAY_REASON,    SlaDelayCollector(jira, q)),
            CollectorEntry(WidgetId.AVG_RESOLUTION_TYPE, ResolutionCollector(jira, q)),
            CollectorEntry(WidgetId.RECENT_ISSUES,       RecentCollector(jira, q)),
        ]

    def monthly_collectors(self, q: ResolvedQueries, now: datetime) -> list[tuple[list[WidgetId], object]]:
        jira = self._jira
        return [
            ([WidgetId.SLA_INITIAL_RESPONSE, WidgetId.SLA_RESOLUTION_MONTHLY], MonthlyCollector(jira, q, now)),
            ([WidgetId.MONTHLY_CREATED, WidgetId.MONTHLY_RESOLVED],             MonthlyCountCollector(jira, q, now)),
        ]
