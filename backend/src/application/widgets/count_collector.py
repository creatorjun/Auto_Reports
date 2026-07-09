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
)
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import (
    JIRA_MAX_RESULTS_DEFAULT,
    JIRA_MAX_RESULTS_LARGE,
    SUMMARY_TRUNCATE_LEN,
)

logger = logging.getLogger(__name__)


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
        counts = await asyncio.gather(
            *[self._jira.get_issue_count(jql) for jql in self._queries.values()]
        )
        breakdown = {label: count for label, count in zip(labels, counts) if count > 0}
        total = sum(breakdown.values())
        logger.info(f"[{self._name}] {total}건")
        return WidgetResult(
            name=self._name,
            total=total,
            data=BreakdownWidgetData(counts=breakdown),
        )


class SlaMetVsViolatedCollector(AbstractWidgetCollector):
    def __init__(
        self,
        jira: JiraPort,
        q: ResolvedQueries,
        sla_initial_response_field_id: str,
        sla_resolution_field_id: str,
    ):
        self._jira = jira
        self._q = q
        self._initial_fid = sla_initial_response_field_id
        self._resolution_fid = sla_resolution_field_id

    async def collect(self) -> WidgetResult[SlaMetVsViolatedWidgetData]:
        fields_str = f"summary,issuetype,status,created,resolutiondate,{self._initial_fid},{self._resolution_fid}"
        jql = self._q.w9_sla()
        issues = await self._jira.get_issues(jql, max_results=JIRA_MAX_RESULTS_LARGE, fields=fields_str)

        total_violations = 0
        initial_response_violations = 0
        resolution_violations = 0

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_response_sla = fields.get(self._initial_fid)
            resolution_sla = fields.get(self._resolution_fid)
            initial_breached = self._is_sla_breached(initial_response_sla)
            resolution_breached = self._is_sla_breached(resolution_sla)
            if initial_response_sla is not None and initial_breached:
                initial_response_violations += 1
            if resolution_sla is not None and resolution_breached:
                resolution_violations += 1
            if (initial_response_sla is not None and initial_breached) or (
                resolution_sla is not None and resolution_breached
            ):
                total_violations += 1

        violation_distribution: list[SlaMetVsViolatedEntry] = []
        if total_violations > 0:
            if initial_response_violations > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="최초 응답 SLA",
                        field_id=self._initial_fid,
                        count=initial_response_violations,
                        rate=round(initial_response_violations / total_violations * 100, 1),
                    )
                )
            if resolution_violations > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="해결 시간 SLA",
                        field_id=self._resolution_fid,
                        count=resolution_violations,
                        rate=round(resolution_violations / total_violations * 100, 1),
                    )
                )

        logger.info(
            f"[w9] 위반 {total_violations}건 (최초응답 {initial_response_violations}건 / 해결시간 {resolution_violations}건)"
        )
        return WidgetResult(
            name="SLA 준수 vs 위반",
            total=total_violations,
            jql=jql,
            data=SlaMetVsViolatedWidgetData(
                initial_response_violations=initial_response_violations,
                resolution_violations=resolution_violations,
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
