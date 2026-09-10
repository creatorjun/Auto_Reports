# backend/src/application/use_cases/get_report_chart_issues.py
from datetime import datetime, time
from typing import Any

from src.application.errors import EntityNotFoundError
from src.application.ports.jira_port import JiraIssue, JiraIssueField, JiraPort
from src.application.services.query_builder import WidgetQueryBuilder, is_dashboard_excluded_issue_type
from src.application.services.report_issue_metrics import resolution_elapsed
from src.application.use_cases.get_report import GetReportUseCase
from src.application.widgets.redeployment_collector import RedeploymentAnalyticsCollector
from src.domain.constants import JIRA_MAX_RESULT, KST
from src.domain.entities.report import Report, ReportScope
from src.domain.entities.report_chart import (
    ReportChartIssue,
    ReportChartIssueResult,
    ReportChartKind,
    ReportChartSelection,
)
from src.domain.value_objects.widget_id import WidgetId

_WIDGETS = {
    ReportChartKind.SLA_INITIAL: WidgetId.SLA_INITIAL_RESPONSE,
    ReportChartKind.SLA_RESOLUTION: WidgetId.SLA_RESOLUTION_MONTHLY,
    ReportChartKind.RESOLUTION_TYPE: WidgetId.AVG_RESOLUTION_TYPE,
    ReportChartKind.REDEPLOYMENT: WidgetId.REDEPLOYMENT_ANALYTICS,
}
_ANALYTICS_TYPES = frozenset({"개선", "인시던트", "서비스 요청"})
_HIDDEN_FILTER_TYPES = frozenset({"승인된 서비스 요청", "케이스"})
_DETAIL_FIELDS = frozenset({
    JiraIssueField.SUMMARY,
    JiraIssueField.ISSUE_TYPE,
    JiraIssueField.STATUS,
    JiraIssueField.CREATED,
    JiraIssueField.RESOLVED,
})


def _value(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _timestamp(value: Any) -> str | None:
    return str(value)[:16].replace("T", " ") if value else None


class GetReportChartIssuesUseCase:
    def __init__(self, reports: GetReportUseCase, jira: JiraPort, query_builder: WidgetQueryBuilder):
        self._reports = reports
        self._jira = jira
        self._query_builder = query_builder

    async def execute(self, report_id: int, selection: ReportChartSelection) -> ReportChartIssueResult:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise EntityNotFoundError("Report", report_id)
        if report.scope != ReportScope.ANNUAL or report.report_year is None:
            raise ValueError("연간 보고서에서만 그래프 상세를 조회할 수 있습니다.")
        if selection.month is not None and selection.month > report.week_end.month:
            raise ValueError("보고서 집계 기간에 포함되지 않는 월입니다.")
        widget = report.widgets.get(_WIDGETS[selection.chart])
        if widget is None or widget.data is None:
            raise EntityNotFoundError("Report chart", selection.chart.value)
        yearly_data = _value(report.widgets.get(WidgetId.YEARLY_CREATED), "data")
        issue_types = _value(yearly_data, "issue_types", []) or []
        controlled = {
            name for name in issue_types
            if not is_dashboard_excluded_issue_type(name) and name not in _HIDDEN_FILTER_TYPES
        }
        queries = self._query_builder.build(
            datetime.combine(report.week_end, time.min),
            week_start_override=datetime.combine(report.week_start, time.min),
            issue_types_override=issue_types,
        )
        if selection.chart == ReportChartKind.REDEPLOYMENT:
            details = await RedeploymentAnalyticsCollector(self._jira, queries).load_details(fresh=True)
            candidates = [ReportChartIssue(
                key=detail.key, summary=detail.summary, type=detail.type,
                resolved=detail.resolved, month=detail.month, cause=detail.cause,
                assignee=detail.assignee, partners=detail.partners, priority=detail.priority,
            ) for detail in details]
            source_total = len(candidates)
            collection_limit = None
            truncated = False
        elif selection.chart == ReportChartKind.RESOLUTION_TYPE:
            jql = queries.w14_resolution_resolved()
            page = await self._jira.get_report_chart_issues(
                jql, max_results=JIRA_MAX_RESULT,
                fields=_DETAIL_FIELDS,
            )
            raw = page.issues
            truncated = page.has_more
            source_total = len(raw) + int(truncated)
            candidates = []
            now = datetime.now()
            for issue in raw:
                elapsed = resolution_elapsed(issue.created, issue.resolved, now)
                if elapsed is None:
                    continue
                hours, month = elapsed
                if selection.semester is not None and (month <= 6) != (selection.semester == "h1"):
                    continue
                candidates.append(self._issue(issue, elapsed_hours=round(hours, 1)))
            collection_limit = JIRA_MAX_RESULT
        else:
            jql = queries.w10_w11_monthly_candidates(report.report_year, selection.month)
            page = await self._jira.get_report_chart_issues(
                jql, max_results=JIRA_MAX_RESULT,
                fields=_DETAIL_FIELDS, with_sla=True,
            )
            raw = page.issues
            truncated = page.has_more
            source_total = len(raw) + int(truncated)
            candidates = [self._issue(
                issue, sla_met=not (
                    issue.initial_response_breached
                    if selection.chart == ReportChartKind.SLA_INITIAL
                    else issue.resolution_breached
                ),
            ) for issue in raw]
            collection_limit = JIRA_MAX_RESULT
        issues = [issue for issue in candidates if self._matches(issue, selection, controlled, report.report_year)]
        return ReportChartIssueResult(
            issues=issues,
            snapshot_count=self._snapshot_count(widget.data, selection, controlled, report.report_year),
            current_count=len(issues),
            source_total=source_total,
            source_total_exact=not truncated,
            collection_limit=collection_limit,
            truncated=truncated,
            queried_at=datetime.now(KST).isoformat(),
            snapshot_at=report.report_date,
        )

    @staticmethod
    def _issue(issue: JiraIssue, **extra: Any) -> ReportChartIssue:
        return ReportChartIssue(
            key=issue.key, summary=issue.summary,
            type=issue.issue_type or "기타",
            status=issue.status or None,
            created=_timestamp(issue.created), resolved=_timestamp(issue.resolved),
            **extra,
        )

    @staticmethod
    def _includes_type(issue_type: str, selection: ReportChartSelection, controlled: set[str]) -> bool:
        return (
            not is_dashboard_excluded_issue_type(issue_type)
            and (selection.issue_type is None or issue_type == selection.issue_type)
            and (selection.selected_types is None or issue_type not in controlled or issue_type in selection.selected_types)
        )

    @classmethod
    def _matches(cls, issue: Any, selection: ReportChartSelection, controlled: set[str], year: int) -> bool:
        if not cls._includes_type(_value(issue, "type", ""), selection, controlled):
            return False
        if selection.selected_statuses is not None and (_value(issue, "status") or "기타") not in selection.selected_statuses:
            return False
        if selection.sla_status != "all" and _value(issue, "sla_met") != (selection.sla_status == "met"):
            return False
        if selection.chart != ReportChartKind.REDEPLOYMENT:
            return True
        if selection.month is not None or selection.cause is not None or selection.assignee is not None:
            if _value(issue, "type") not in _ANALYTICS_TYPES:
                return False
        return (
            (selection.month is None or str(_value(issue, "month", "")).startswith(f"{year}-{selection.month:02d}"))
            and (selection.partner is None or selection.partner in (_value(issue, "partners", []) or []))
            and (selection.cause is None or selection.cause == _value(issue, "cause"))
            and (selection.assignee is None or selection.assignee == _value(issue, "assignee"))
        )

    @classmethod
    def _snapshot_count(cls, data: Any, selection: ReportChartSelection, controlled: set[str], year: int) -> int | None:
        if selection.selected_statuses == ():
            return 0
        if selection.chart in (ReportChartKind.SLA_INITIAL, ReportChartKind.SLA_RESOLUTION):
            entry = next((entry for entry in _value(data, "monthly", []) or [] if _value(entry, "year") == year and _value(entry, "month_num") == selection.month), None)
            if entry is None:
                return None
            by_type = _value(entry, "by_type")
            if selection.selected_statuses is not None:
                by_status_type = _value(entry, "by_status_type")
                if not by_status_type and _value(entry, "total", 0):
                    return None
                stats = [
                    value
                    for status, values in (by_status_type or {}).items()
                    if status in selection.selected_statuses
                    for name, value in values.items()
                    if cls._includes_type(name, selection, controlled)
                ]
                total = sum(_value(value, "total", 0) or 0 for value in stats)
                met = sum(_value(value, "met", 0) or 0 for value in stats)
            elif by_type and (selection.issue_type is not None or selection.selected_types is not None):
                stats = [value for name, value in by_type.items() if cls._includes_type(name, selection, controlled)]
                if selection.issue_type is None and _value(entry, "always_included") is not None:
                    stats.append(_value(entry, "always_included"))
                if selection.issue_type is not None and selection.issue_type not in by_type:
                    return None
                total = sum(_value(value, "total", 0) or 0 for value in stats)
                met = sum(_value(value, "met", 0) or 0 for value in stats)
            elif selection.issue_type is not None or selection.selected_types is not None:
                return None
            else:
                total, met = _value(entry, "total", 0), _value(entry, "met", 0)
            return met if selection.sla_status == "met" else total - met if selection.sla_status == "violated" else total
        if selection.chart == ReportChartKind.RESOLUTION_TYPE:
            values = _value(data, "by_type") if selection.semester is None else (_value(data, "by_semester", {}) or {}).get(selection.semester)
            if values is None:
                return None
            if selection.selected_statuses is not None:
                by_status_type = (
                    _value(data, "by_status_type")
                    if selection.semester is None
                    else (_value(data, "by_semester_status_type", {}) or {}).get(selection.semester)
                )
                if not by_status_type and any(_value(value, "count", 0) for value in values.values()):
                    return None
                return sum(
                    _value(value, "count", 0) or 0
                    for status, by_type in (by_status_type or {}).items()
                    if status in selection.selected_statuses
                    for name, value in by_type.items()
                    if cls._includes_type(name, selection, controlled)
                )
            return sum(_value(value, "count", 0) or 0 for name, value in values.items() if cls._includes_type(name, selection, controlled))
        if selection.partner is not None:
            counts = (_value(data, "partner_matrix", {}) or {}).get(selection.partner, {})
            return sum(count for name, count in counts.items() if cls._includes_type(name, selection, controlled))
        if selection.month is not None:
            entry = next((entry for entry in _value(data, "monthly", []) or [] if _value(entry, "year") == year and _value(entry, "month_num") == selection.month), None)
            if entry is None:
                return None
            return sum(count for name, count in (_value(entry, "by_type", {}) or {}).items() if cls._includes_type(name, selection, controlled))
        if selection.cause is not None or selection.assignee is not None:
            if selection.issue_type is None and selection.selected_types is None:
                field, key = ("by_cause", selection.cause) if selection.cause is not None else ("by_assignee", selection.assignee)
                return (_value(data, field, {}) or {}).get(key, 0)
            issues = _value(data, "latest_issues", []) or []
            if len(issues) == _value(data, "analytics_total"):
                return sum(cls._matches(issue, selection, controlled, year) for issue in issues)
            return None
        if selection.issue_type is None and selection.selected_types is None:
            return _value(data, "redeployment_total")
        issues = _value(data, "latest_issues", []) or []
        if len(issues) == _value(data, "redeployment_total"):
            return sum(cls._matches(issue, selection, controlled, year) for issue in issues)
        return None
