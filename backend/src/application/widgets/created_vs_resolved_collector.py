# backend/src/application/widgets/created_vs_resolved_collector.py
import asyncio
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import CreatedVsResolvedWidgetData, IssueDetail
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class CreatedVsResolvedCollector(AbstractWidgetCollector):
    """w3: 주간 생성 vs 해결 수 및 이슈 상세."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[CreatedVsResolvedWidgetData]:
        created_jql, resolved_jql = self._q.w3_created_vs_resolved()
        created_issues, resolved_issues = await asyncio.gather(
            self._jira.get_issues(created_jql, max_results=200, fields="summary,issuetype,status,created"),
            self._jira.get_issues(resolved_jql, max_results=200, fields="summary,issuetype,status,created,resolutiondate"),
        )
        now_ts = datetime.now()

        def _to_detail(issue: dict) -> IssueDetail:
            fields = issue.get("fields") or {}
            created = fields.get("created", "")
            elapsed = (now_ts - datetime.fromisoformat(created[:19])).days if created else 0
            return IssueDetail(
                key=issue.get("key", ""),
                summary=(fields.get("summary") or "")[:60],
                type=(fields.get("issuetype") or {}).get("name", "기타"),
                status=(fields.get("status") or {}).get("name", "기타"),
                created=created[:16].replace("T", " "),
                elapsed_days=elapsed,
            )

        created_details  = [_to_detail(i) for i in created_issues]
        resolved_details = [_to_detail(i) for i in resolved_issues]
        logger.info(f"[w3-생성vs해결] 생성 {len(created_details)}건 / 해결 {len(resolved_details)}건")
        return WidgetResult(
            name="주간 생성 vs 해결",
            total=len(created_details),
            jql=created_jql,
            data=CreatedVsResolvedWidgetData(
                created=len(created_details),
                resolved=len(resolved_details),
                created_details=created_details,
                resolved_details=resolved_details,
            ),
        )
