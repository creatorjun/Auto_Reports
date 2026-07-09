# backend/src/application/widgets/recent_collector.py
import logging
from datetime import datetime

from src.application.services.query_builder import ResolvedQueries
from src.application.widgets.base import AbstractWidgetCollector
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueWidgetData, RecentIssueDetail
from src.domain.ports.jira_port import JiraPort
from src.shared.constants import (
    JIRA_RECENT_PAGE_SIZE,
    STAGE_MAP,
    SUMMARY_TRUNCATE_LEN,
)

logger = logging.getLogger(__name__)


def _user_name(value: object) -> str:
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
    """w12: 최근 활성 이슈 목록."""

    def __init__(
        self,
        jira: JiraPort,
        q: ResolvedQueries,
        tac_assignee_field_id: str,
        qa_assignee_field_id: str,
    ):
        self._jira = jira
        self._q = q
        self._tac_field = tac_assignee_field_id
        self._qa_field = qa_assignee_field_id

    async def collect(self) -> WidgetResult[RecentIssueWidgetData]:
        jql = self._q.w12_recent()
        issues = await self._jira.get_issues(
            jql,
            max_results=JIRA_RECENT_PAGE_SIZE * 2,
            fields=(
                f"summary,issuetype,status,created,reporter,assignee,"
                f"{self._tac_field},{self._qa_field}"
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
            tac_team = _pick_user(fields, self._tac_field, self._qa_field, "assignee")
            issue_details.append(
                RecentIssueDetail(
                    key=issue.get("key", ""),
                    summary=(fields.get("summary") or "")[:SUMMARY_TRUNCATE_LEN],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=status_name,
                    stage_index=STAGE_MAP.get(status_name, 0),
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
