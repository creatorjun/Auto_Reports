# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueWidgetData, RecentIssueDetail
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)

# 상태명 → 단계(칸 갯수) 매핑
# 전체 8칸 기준: 0 = 할 일, 1 = 이슈 리뷰 중, ..., 7 = 구현 수락
_STAGE_MAP: dict[str, int] = {
    "할 일":           0,
    "이슈 리뷰 중":   1,
    "자료 요청 중":   2,
    "결과 대기 중":   3,
    "연구소 대기 중":  4,
    "연구소 검토 중":  5,
    "배포 파일 검토 중": 6,
    "구현 중":        7,
    "구현 완료":      8,
}


class RecentCollector(AbstractWidgetCollector):
    """w13: 최근 활성 이슈 목록 (최신 50건)."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w13_recent()
        issues = await self._jira.get_issues(
            jql, max_results=50, fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        issue_details = []
        for issue in issues:
            fields = issue.get("fields") or {}
            created = fields.get("created", "")
            status_name = (fields.get("status") or {}).get("name", "기타")
            elapsed_days = (
                (now_ts - datetime.fromisoformat(created[:19])).days if created else 0
            )
            issue_details.append(
                RecentIssueDetail(
                    key=issue.get("key", ""),
                    summary=(fields.get("summary") or "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=status_name,
                    stage_index=_STAGE_MAP.get(status_name, 0),
                    created=created[:16].replace("T", " "),
                    elapsed_days=elapsed_days,
                )
            )
        total = len(issue_details)
        logger.info(f"[w13-최근이슈] {total}건")
        return WidgetResult(
            name="최근 활성 이슈",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=issue_details),
        )
