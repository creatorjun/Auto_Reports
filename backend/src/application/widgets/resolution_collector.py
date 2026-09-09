# backend/src/application/widgets/resolution_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import ResolutionTypeEntry, ResolutionTypeWidgetData
from src.application.ports.jira_port import JiraIssueField, JiraPort

logger = logging.getLogger(__name__)


class ResolutionCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries, now: datetime):
        self._jira = jira
        self._q = q
        self._now = now.replace(tzinfo=None)

    async def collect(self) -> WidgetResult[ResolutionTypeWidgetData]:
        jql = self._q.w14_resolution_resolved()
        issues = await self._jira.get_issues(
            jql,
            max_results=None,
            fields=frozenset({
                JiraIssueField.SUMMARY,
                JiraIssueField.ISSUE_TYPE,
                JiraIssueField.STATUS,
                JiraIssueField.CREATED,
                JiraIssueField.RESOLVED,
            }),
        )
        by_type: dict[str, list[float]] = {}
        by_semester: dict[str, dict[str, list[float]]] = {"h1": {}, "h2": {}}
        by_status_type: dict[str, dict[str, list[float]]] = {}
        by_semester_status_type: dict[str, dict[str, dict[str, list[float]]]] = {
            "h1": {},
            "h2": {},
        }
        for issue in issues:
            itype = issue.issue_type or "기타"
            status = issue.status or "기타"
            created = issue.created
            resolved = issue.resolved
            if not created:
                continue
            end_ts = datetime.fromisoformat(resolved[:19]) if resolved else self._now
            elapsed = (end_ts - datetime.fromisoformat(created[:19])).total_seconds() / 3600
            by_type.setdefault(itype, []).append(elapsed)
            semester = "h1" if end_ts.month <= 6 else "h2"
            by_semester[semester].setdefault(itype, []).append(elapsed)
            by_status_type.setdefault(status, {}).setdefault(itype, []).append(elapsed)
            by_semester_status_type[semester].setdefault(status, {}).setdefault(itype, []).append(elapsed)
        result = self._summarize(by_type)
        semester_result = {
            semester: self._summarize(values)
            for semester, values in by_semester.items()
        }
        total = sum(e.count for e in result.values())
        logger.info(f"[w14-평균처리일] {total}건")
        return WidgetResult(
            name="유형별 평균 처리일",
            total=total,
            jql=jql,
            data=ResolutionTypeWidgetData(
                by_type=result,
                by_semester=semester_result,
                by_status_type=self._summarize_nested(by_status_type),
                by_semester_status_type={
                    semester: self._summarize_nested(values)
                    for semester, values in by_semester_status_type.items()
                },
            ),
        )

    @staticmethod
    def _summarize(values: dict[str, list[float]]) -> dict[str, ResolutionTypeEntry]:
        result: dict[str, ResolutionTypeEntry] = {}
        for issue_type, hours_list in values.items():
            avg_hours = sum(hours_list) / len(hours_list)
            result[issue_type] = ResolutionTypeEntry(
                avg_days=round(avg_hours / 24, 1),
                avg_hours=round(avg_hours, 1),
                count=len(hours_list),
            )
        return result

    @classmethod
    def _summarize_nested(
        cls,
        values: dict[str, dict[str, list[float]]],
    ) -> dict[str, dict[str, ResolutionTypeEntry]]:
        return {
            status: cls._summarize(type_values)
            for status, type_values in values.items()
        }
