# backend/src/application/widgets/resolution_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import ResolutionTypeEntry, ResolutionTypeWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class ResolutionCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[ResolutionTypeWidgetData]:
        jql = self._q.w10_11_resolved()
        issues = await self._jira.get_issues(
            jql,
            max_results=200,
            fields="summary,issuetype,created,resolutiondate",
        )
        type_hours: dict[str, list[float]] = {}
        for issue in issues:
            fields = issue.get("fields", {})
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created")
            resolved = fields.get("resolutiondate")
            if not created or not resolved:
                continue
            hours = (
                datetime.fromisoformat(resolved[:19]) - datetime.fromisoformat(created[:19])
            ).total_seconds() / 3600
            type_hours.setdefault(issue_type, []).append(round(hours, 2))

        breakdown: dict[str, ResolutionTypeEntry] = {}
        for issue_type, hour_list in type_hours.items():
            average = sum(hour_list) / len(hour_list)
            breakdown[issue_type] = ResolutionTypeEntry(
                avg_days=round(average / 24, 1),
                avg_hours=round(average, 1),
                count=len(hour_list),
            )
        total = sum(entry.count for entry in breakdown.values())
        logger.info(f"[W10] {total}건")
        return WidgetResult(
            name="유형별 평균 처리일",
            total=total,
            jql=jql,
            data=ResolutionTypeWidgetData(by_type=breakdown),
        )
