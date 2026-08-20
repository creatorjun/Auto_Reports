# backend/src/application/widgets/resolution_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import ResolutionTypeEntry, ResolutionTypeWidgetData
from src.application.ports.jira_port import JiraPort
from src.domain.constants import JIRA_MAX_RESULT

logger = logging.getLogger(__name__)


class ResolutionCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[ResolutionTypeWidgetData]:
        jql = self._q.w14_resolution_resolved()
        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULT, fields="summary,issuetype,created,resolutiondate",
        )
        now_ts = datetime.now()
        by_type: dict[str, list[float]] = {}
        for issue in issues:
            fields = issue.get("fields") or {}
            itype = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created", "")
            resolved = fields.get("resolutiondate", "")
            if not created:
                continue
            end_ts = datetime.fromisoformat(resolved[:19]) if resolved else now_ts
            elapsed = (end_ts - datetime.fromisoformat(created[:19])).total_seconds() / 3600
            by_type.setdefault(itype, []).append(elapsed)
        result: dict[str, ResolutionTypeEntry] = {}
        for itype, hours_list in by_type.items():
            avg_hours = sum(hours_list) / len(hours_list)
            result[itype] = ResolutionTypeEntry(
                avg_days=round(avg_hours / 24, 1),
                avg_hours=round(avg_hours, 1),
                count=len(hours_list),
            )
        total = sum(e.count for e in result.values())
        logger.info(f"[w14-평균처리일] {total}건")
        return WidgetResult(
            name="유형별 평균 처리일",
            total=total,
            jql=jql,
            data=ResolutionTypeWidgetData(by_type=result),
        )
