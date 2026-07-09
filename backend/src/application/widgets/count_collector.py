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
    """
    w9: SLA 준수 vs 위반

    위반 유형을 세 가지로 정확히 분리합니다:
      1) 최초 응답 SLA만 위반
      2) 해결 시간 SLA만 위반
      3) 둘 다 위반 (복합)

    total == sum(distribution counts) 를 항상 보장합니다.
    """

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
        fields_str = (
            f"summary,issuetype,status,created,resolutiondate,"
            f"{self._initial_fid},{self._resolution_fid}"
        )
        jql = self._q.w9_sla()
        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULTS_LARGE, fields=fields_str
        )

        only_initial = 0
        only_resolution = 0
        both = 0

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_breached = self._is_sla_breached(fields.get(self._initial_fid))
            resolution_breached = self._is_sla_breached(fields.get(self._resolution_fid))

            if initial_breached and resolution_breached:
                both += 1
            elif initial_breached:
                only_initial += 1
            elif resolution_breached:
                only_resolution += 1

        total_violations = only_initial + only_resolution + both

        violation_distribution: list[SlaMetVsViolatedEntry] = []
        if total_violations > 0:
            if only_initial > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="최초 응답 SLA",
                        field_id=self._initial_fid,
                        count=only_initial,
                        rate=round(only_initial / total_violations * 100, 1),
                    )
                )
            if only_resolution > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="해결 시간 SLA",
                        field_id=self._resolution_fid,
                        count=only_resolution,
                        rate=round(only_resolution / total_violations * 100, 1),
                    )
                )
            if both > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="둘 다 위반",
                        field_id="both",
                        count=both,
                        rate=round(both / total_violations * 100, 1),
                    )
                )

        logger.info(
            f"[w9] 위반 {total_violations}건 "
            f"(최초응답만 {only_initial}건 / 해결시ac04만 {only_resolution}건 / 둘다 {both}건)"
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
