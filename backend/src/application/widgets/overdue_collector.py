# backend/src/application/widgets/overdue_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import OverdueIssueDetail, OverdueWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class OverdueCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries, sla_threshold_days: int):
        self._jira = jira
        self._q = q
        self._sla_threshold_days = sla_threshold_days

    async def collect(self) -> WidgetResult[OverdueWidgetData]:
        jql = self._q.w1_overdue()
        issues = await self._jira.get_issues(
            jql,
            max_results=500,
            fields="summary,issuetype,status,created,resolutiondate",
        )
        total = len(issues)
        by_type: dict[str, dict[str, int]] = {}
        details: list[OverdueIssueDetail] = []
        now_ts = datetime.now()
        thr_hours = self._sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            status = (fields.get("status") or {}).get("name", "기타")
            created = fields.get("created", "")
            resolved = fields.get("resolutiondate")
            summary = fields.get("summary", "")[:60]

            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_h = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0
            response_status = "종료" if resolved else "진행 중"

            by_type.setdefault(issue_type, {})
            by_type[issue_type][status] = by_type[issue_type].get(status, 0) + 1

            details.append(
                OverdueIssueDetail(
                    key=key,
                    summary=summary,
                    type=issue_type,
                    created=created[:16].replace("T", " ") if created else "",
                    resp_status=response_status,
                    over_h=over_h,
                )
            )

        details.sort(key=lambda item: item.over_h, reverse=True)
        logger.info(f"[W1] {total}건")
        return WidgetResult(
            name="생성 1달 이상 된 이슈",
            total=total,
            jql=jql,
            data=OverdueWidgetData(by_type=by_type, issue_details=details),
        )
