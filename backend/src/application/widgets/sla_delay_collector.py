# backend/src/application/widgets/sla_delay_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    SlaDelayWidgetData,
    SlaDistributionEntry,
    SlaViolatedIssueDetail,
)
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class SlaDelayCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries, sla_threshold_days: int):
        self._jira = jira
        self._q = q
        self._sla_threshold_days = sla_threshold_days

    async def collect(self) -> WidgetResult[SlaDelayWidgetData]:
        jql = self._q.w7_sla_violated()
        issues = await self._jira.get_issues(
            jql,
            max_results=500,
            fields="summary,issuetype,status,created",
        )
        by_status: dict[str, int] = {}
        details: list[SlaViolatedIssueDetail] = []
        now_ts = datetime.now()
        thr_hours = self._sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            status = (fields.get("status") or {}).get("name", "기타")
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created", "")

            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_h = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0

            by_status[status] = by_status.get(status, 0) + 1
            details.append(
                SlaViolatedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=issue_type,
                    status=status,
                    created=created[:16].replace("T", " ") if created else "",
                    over_h=over_h,
                )
            )

        total = len(issues)
        details.sort(key=lambda item: item.over_h, reverse=True)
        distribution = [
            SlaDistributionEntry(
                status=status,
                count=count,
                rate=round(count / total * 100, 1) if total > 0 else 0.0,
            )
            for status, count in sorted(by_status.items(), key=lambda item: item[1], reverse=True)
        ]

        logger.info(f"[W7] SLA 위반 {total}건 / 상태 {len(by_status)}종")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            data=SlaDelayWidgetData(
                by_status=dict(sorted(by_status.items(), key=lambda item: item[1], reverse=True)),
                distribution=distribution,
                issue_details=details,
            ),
        )
