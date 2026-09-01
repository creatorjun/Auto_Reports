# backend/src/application/widgets/redeployment_collector.py
import asyncio
from collections import Counter, defaultdict
from typing import Any

from src.application.ports.jira_port import JiraPort
from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.constants import JIRA_MAX_RESULT, SUMMARY_TRUNCATE_LEN
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    RedeploymentAnalyticsWidgetData,
    RedeploymentIssueDetail,
    RedeploymentMonthlyEntry,
)

_DASHBOARD_ID = "11218"
_MONTH_FIELD = "customfield_12421"
_CAUSE_FIELD = "customfield_11885"
_PARTNER_FIELD = "customfield_10859"
_ANALYTICS_TYPES = frozenset({"\uac1c\uc120", "\uc778\uc2dc\ub358\ud2b8", "\uc11c\ube44\uc2a4 \uc694\uccad"})


class RedeploymentAnalyticsCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, queries: ResolvedQueries):
        self._jira = jira
        self._queries = queries

    async def collect(self) -> WidgetResult[RedeploymentAnalyticsWidgetData]:
        resolved_jql = self._queries.w15_redeployment_resolved()
        redeployment_jql = self._queries.w15_redeployment_issues()
        analytics_jql = self._queries.w15_redeployment_analytics()
        resolved_total, redeployment_total, issues = await asyncio.gather(
            self._jira.get_issue_count(resolved_jql),
            self._jira.get_issue_count(redeployment_jql),
            self._jira.get_issues(
                f"{redeployment_jql} ORDER BY resolved DESC",
                max_results=JIRA_MAX_RESULT,
                fields=(
                    "summary,issuetype,priority,resolutiondate,assignee,"
                    f"{_MONTH_FIELD},{_CAUSE_FIELD},{_PARTNER_FIELD}"
                ),
            ),
        )
        references = self._asset_references(issues)
        asset_labels = await self._jira.get_asset_object_labels(references)
        details = [self._to_detail(issue, asset_labels) for issue in issues]
        details.sort(key=lambda issue: issue.resolved, reverse=True)
        analytics_details = [issue for issue in details if issue.type in _ANALYTICS_TYPES]
        monthly = self._monthly(analytics_details, self._queries.week_end.year)
        by_cause = dict(Counter(issue.cause for issue in analytics_details).most_common())
        by_assignee = dict(Counter(issue.assignee for issue in analytics_details).most_common())
        partner_matrix = self._partner_matrix(details)
        rate = round(redeployment_total / resolved_total * 100, 1) if resolved_total else 0.0
        return WidgetResult(
            name="\uc7ac\ubc30\ud3ec \ud488\uc9c8 \uc9c0\ud45c",
            total=redeployment_total,
            jql=redeployment_jql,
            data=RedeploymentAnalyticsWidgetData(
                dashboard_id=_DASHBOARD_ID,
                resolved_total=resolved_total,
                redeployment_total=redeployment_total,
                redeployment_rate=rate,
                analytics_total=len(analytics_details),
                monthly=monthly,
                by_cause=by_cause,
                by_assignee=by_assignee,
                partner_matrix=partner_matrix,
                latest_issues=analytics_details[:5],
                source_jqls={
                    "resolved": resolved_jql,
                    "redeployed": redeployment_jql,
                    "analytics": analytics_jql,
                    "kpi_reference": "project = SLCQA AND issuekey = SLCQA-181",
                },
            ),
        )

    @staticmethod
    def _asset_references(issues: list[dict[str, Any]]) -> list[tuple[str, str]]:
        references: list[tuple[str, str]] = []
        for issue in issues:
            fields = issue.get("fields") or {}
            for partner in fields.get(_PARTNER_FIELD) or []:
                workspace_id = str(partner.get("workspaceId") or "")
                object_id = str(partner.get("objectId") or "")
                if workspace_id and object_id:
                    references.append((workspace_id, object_id))
        return list(dict.fromkeys(references))

    @staticmethod
    def _option_value(value: Any, fallback: str) -> str:
        if isinstance(value, dict):
            return str(value.get("value") or fallback)
        if value:
            return str(value)
        return fallback

    @staticmethod
    def _to_detail(
        issue: dict[str, Any],
        asset_labels: dict[tuple[str, str], str],
    ) -> RedeploymentIssueDetail:
        fields = issue.get("fields") or {}
        resolved_raw = str(fields.get("resolutiondate") or "")
        resolved_month = resolved_raw[:7]
        month = RedeploymentAnalyticsCollector._option_value(
            fields.get(_MONTH_FIELD),
            resolved_month or "\ubbf8\uc9c0\uc815",
        )
        partners: list[str] = []
        for partner in fields.get(_PARTNER_FIELD) or []:
            reference = (
                str(partner.get("workspaceId") or ""),
                str(partner.get("objectId") or ""),
            )
            if all(reference):
                partners.append(asset_labels.get(reference, f"\ud30c\ud2b8\ub108 \uac1d\uccb4 {reference[1]}"))
        return RedeploymentIssueDetail(
            key=str(issue.get("key") or ""),
            summary=str(fields.get("summary") or "")[:SUMMARY_TRUNCATE_LEN],
            type=str((fields.get("issuetype") or {}).get("name") or "\uae30\ud0c0"),
            priority=str((fields.get("priority") or {}).get("name") or "\ubbf8\uc9c0\uc815"),
            resolved=resolved_raw[:16].replace("T", " "),
            month=month,
            cause=RedeploymentAnalyticsCollector._option_value(
                fields.get(_CAUSE_FIELD),
                "\ubbf8\uc9c0\uc815",
            ),
            assignee=str((fields.get("assignee") or {}).get("displayName") or "\ubbf8\uc9c0\uc815"),
            partners=list(dict.fromkeys(partners)) or ["\ubbf8\uc9c0\uc815"],
        )

    @staticmethod
    def _monthly(
        issues: list[RedeploymentIssueDetail],
        year: int,
    ) -> list[RedeploymentMonthlyEntry]:
        counts: dict[int, Counter[str]] = defaultdict(Counter)
        for issue in issues:
            if issue.month.startswith(f"{year}-"):
                try:
                    month_number = int(issue.month[5:7])
                except ValueError:
                    continue
                if 1 <= month_number <= 12:
                    counts[month_number][issue.type] += 1
        return [
            RedeploymentMonthlyEntry(
                month=f"{month_number}\uc6d4",
                year=year,
                month_num=month_number,
                total=sum(counts[month_number].values()),
                by_type=dict(counts[month_number]),
            )
            for month_number in range(1, 13)
        ]

    @staticmethod
    def _partner_matrix(
        issues: list[RedeploymentIssueDetail],
    ) -> dict[str, dict[str, int]]:
        matrix: dict[str, Counter[str]] = defaultdict(Counter)
        for issue in issues:
            for partner in issue.partners:
                matrix[partner][issue.type] += 1
        return {
            partner: dict(counts)
            for partner, counts in sorted(
                matrix.items(),
                key=lambda item: (-sum(item[1].values()), item[0]),
            )
        }
