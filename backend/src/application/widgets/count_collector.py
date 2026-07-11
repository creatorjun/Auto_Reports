# backend/src/application/widgets/count_collector.py
import asyncio
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    BreakdownWidgetData,
    IssueDetail,
    SimpleIssueWidgetData,
    SlaMetVsViolatedEntry,
    SlaMetVsViolatedWidgetData,
    SlaViolationIssueDetail,
)
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import (
    JIRA_MAX_RESULTS_DEFAULT,
    JIRA_MAX_RESULTS_LARGE,
    SUMMARY_TRUNCATE_LEN,
)

logger = logging.getLogger(__name__)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"


class SimpleCountCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, name: str, jql: str):
        self._jira = jira
        self._name = name
        self._jql = jql

    async def collect(self) -> WidgetResult[None]:
        total = await self._jira.get_issue_count(self._jql)
        logger.info(f"[{self._name}] {total}건")
        return WidgetResult(name=self._name, total=total, jql=self._jql)


class SimpleWithDetailsCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, name: str, jql: str):
        self._jira = jira
        self._name = name
        self._jql = jql

    async def collect(self) -> WidgetResult[SimpleIssueWidgetData]:
        issues = await self._jira.get_issues(
            self._jql,
            max_results=JIRA_MAX_RESULTS_DEFAULT,
            fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        details: list[IssueDetail] = []
        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            created = fields.get("created") or ""
            elapsed_days = 0
            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_days = (now_ts - created_dt).days
            details.append(
                IssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:SUMMARY_TRUNCATE_LEN],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=(fields.get("status") or {}).get("name", "기타"),
                    created=created[:16].replace("T", " "),
                    elapsed_days=elapsed_days,
                )
            )
        details.sort(key=lambda item: item.elapsed_days, reverse=True)
        total = len(details)
        logger.info(f"[{self._name}] {total}건")
        return WidgetResult(
            name=self._name,
            total=total,
            jql=self._jql,
            data=SimpleIssueWidgetData(issue_details=details),
        )


class BreakdownCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, name: str, queries: dict[str, str]):
        self._jira = jira
        self._name = name
        self._queries = queries

    async def collect(self) -> WidgetResult[BreakdownWidgetData]:
        labels = list(self._queries.keys())
        jqls   = list(self._queries.values())
        counts = await self._jira.get_issue_counts_batch(jqls)
        breakdown = {label: count for label, count in zip(labels, counts) if count > 0}
        total = sum(breakdown.values())
        logger.info(f"[{self._name}] {total}건 (배치 {len(jqls)}건 JQL)")
        return WidgetResult(
            name=self._name,
            total=total,
            data=BreakdownWidgetData(counts=breakdown),
        )


class SlaMetVsViolatedCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[SlaMetVsViolatedWidgetData]:
        jql = self._q.w9_sla()
        issues = await self._jira.get_issues_with_sla(jql, max_results=JIRA_MAX_RESULTS_LARGE)

        only_initial_issues: list[SlaViolationIssueDetail] = []
        only_resolution_issues: list[SlaViolationIssueDetail] = []
        both_issues: list[SlaViolationIssueDetail] = []

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_breached    = self._is_sla_breached(fields.get(_SLA_INITIAL_KEY))
            resolution_breached = self._is_sla_breached(fields.get(_SLA_RESOLUTION_KEY))

            if not (initial_breached or resolution_breached):
                continue

            created_raw = fields.get("created") or ""
            detail = SlaViolationIssueDetail(
                key=issue.get("key", ""),
                summary=(fields.get("summary") or "")[:SUMMARY_TRUNCATE_LEN],
                type=(fields.get("issuetype") or {}).get("name", "기타"),
                status=(fields.get("status") or {}).get("name", "기타"),
                created=created_raw[:16].replace("T", " "),
            )

            if initial_breached and resolution_breached:
                both_issues.append(detail)
            elif initial_breached:
                only_initial_issues.append(detail)
            else:
                only_resolution_issues.append(detail)

        only_initial    = len(only_initial_issues)
        only_resolution = len(only_resolution_issues)
        both            = len(both_issues)
        total_violations = only_initial + only_resolution + both

        violation_distribution: list[SlaMetVsViolatedEntry] = []
        if total_violations > 0:
            if only_initial > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="최초 응답 SLA",
                        field_id=_SLA_INITIAL_KEY,
                        count=only_initial,
                        rate=round(only_initial / total_violations * 100, 1),
                        issue_details=only_initial_issues,
                    )
                )
            if only_resolution > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="해결 시간 SLA",
                        field_id=_SLA_RESOLUTION_KEY,
                        count=only_resolution,
                        rate=round(only_resolution / total_violations * 100, 1),
                        issue_details=only_resolution_issues,
                    )
                )
            if both > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="둘 다 위반",
                        field_id="both",
                        count=both,
                        rate=round(both / total_violations * 100, 1),
                        issue_details=both_issues,
                    )
                )

        logger.info(
            f"[w9] 위반 {total_violations}건 "
            f"(최초응답만 {only_initial}건 / 해결시간만 {only_resolution}건 / 둘다 {both}건)"
        )
        return WidgetResult(
            name="SLA 준수 vs 위반",
            total=total_violations,
            jql=jql,
            data=SlaMetVsViolatedWidgetData(
                initial_response_violations=only_initial + both,
                resolution_violations=only_resolution + both,
                both_violations=both,
                violation_distribution=violation_distribution,
            ),
        )

    @staticmethod
    def _is_sla_breached(sla_val: dict | None) -> bool:
        if not sla_val:
            return False
        for cycle in sla_val.get("completedCycles") or []:
            if cycle.get("breached"):
                return True
        ongoing = sla_val.get("ongoingCycle")
        if ongoing and ongoing.get("breached"):
            return True
        return False
