# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueWidgetData, RecentIssueDetail
from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)

_STAGE_MAP: dict[str, int] = {
    "할 일":            0,
    "재오픈":           0,
    "자료 요청 중":    1,
    "이슈 리뷰 중":    2,
    "연구소 대기 중":   3,
    "연구소 검토 중":   3,
    "구현 중":         4,
    "배포 파일 검토 중":  5,
    "결과 대기 중":    6,
}

FIELD_TAC_ASSIGNEE = "customfield_10859"
FIELD_QA_ASSIGNEE  = "customfield_12222"
PAGE_SIZE = 50


def _user_name(value: object) -> str:
    """user 객체(단일 or 리스트) 에서 displayName 추출."""
    if isinstance(value, list):
        for item in value:
            name = _user_name(item)
            if name:
                return name
        return ""
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name") or ""
    return ""


def _pick_user(fields: dict, *field_keys: str) -> str:
    for key in field_keys:
        name = _user_name(fields.get(key))
        if name:
            return name
    return "미지정"


class RecentCollector(AbstractWidgetCollector):
    """w12: 최근 활성 이슈 목록 (최신 100건, 페이지당 50건)."""

    def __init__(self, jira: JiraPort, q: ResolvedQueries):
        self._jira = jira
        self._q = q

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w12_recent()
        issues = await self._jira.get_issues(
            jql,
            max_results=PAGE_SIZE * 2,
            fields=(
                f"summary,issuetype,status,created,reporter,assignee,"
                f"{FIELD_TAC_ASSIGNEE},{FIELD_QA_ASSIGNEE}"
            ),
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

            reporter = _pick_user(fields, "reporter")
            tac_team = _pick_user(
                fields,
                FIELD_TAC_ASSIGNEE,
                FIELD_QA_ASSIGNEE,
                "assignee",
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
                    reporter=reporter,
                    tac_team=tac_team,
                )
            )
        total = len(issue_details)
        logger.info(f"[w12-최근이슈] {total}건")
        return WidgetResult(
            name="최근 활성 이슈",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=issue_details),
        )
