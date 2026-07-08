# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)

STATUS_ORDER = [
    "할 일",
    "이슈 리뷰 중",
    "연구소 대기 중",
    "연구소 검토 중",
    "구현 중",
    "배포 파일 검토 중",
    "자료 요청 중",
    "결과 대기 중",
    "보류 중",
    "영업본부 검토중",
]


class RecentCollector(AbstractWidgetCollector):
    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w11_recent()
        issues = await self._jira.get_issues(
            jql,
            max_results=15,
            fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        details: list[RecentIssueDetail] = []

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            status = (fields.get("status") or {}).get("name", "기타")
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created") or ""
            elapsed_days = 0
            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_days = (now_ts - created_dt).days
            stage_index = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
            details.append(
                RecentIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:50],
                    type=issue_type,
                    status=status,
                    stage_index=stage_index,
                    created=created[:16].replace("T", " ") if created else "",
                    elapsed_days=elapsed_days,
                )
            )

        total = len(details)
        logger.info(f"[W11] 최근 생성 {total}건")
        return WidgetResult(
            name="최근 이슈 현황",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=details),
        )
