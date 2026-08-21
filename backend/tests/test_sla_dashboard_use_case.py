# backend/tests/test_sla_dashboard_use_case.py
import datetime
import pathlib
import sys
import unittest
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.errors import EntityNotFoundError
from src.application.use_cases.sla_dashboard import SlaDashboardUseCase
from src.domain.entities.report import Report
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId


class FakeReports:
    def __init__(self, report: Report | None) -> None:
        self.report = report

    async def get_latest(self) -> Report | None:
        return self.report


class FakeJira:
    def __init__(self) -> None:
        self.issues: list[dict[str, Any]] = []
        self.comments: list[dict[str, Any]] = []
        self.issue_requests: list[tuple[str, int, str]] = []
        self.comment_requests: list[tuple[str, int]] = []

    async def get_issues(
        self,
        jql: str,
        max_results: int,
        fields: str,
    ) -> list[dict[str, Any]]:
        self.issue_requests.append((jql, max_results, fields))
        return self.issues

    async def get_issue_comments(
        self,
        issue_key: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        self.comment_requests.append((issue_key, max_results))
        return self.comments


def recent_detail(key: str, status: str = "할 일") -> RecentIssueDetail:
    return RecentIssueDetail(
        key=key,
        summary="요약",
        type="인시던트",
        status=status,
        stage_index=0,
        created="2026-08-20 09:00",
        elapsed_days=1,
    )


def latest_report(*details: RecentIssueDetail) -> Report:
    return Report(
        id=1,
        week_start=datetime.date(2026, 8, 15),
        week_end=datetime.date(2026, 8, 21),
        report_date="2026-08-21",
        widgets={
            WidgetId.RECENT_ISSUES: WidgetResult(
                name="최근 활성 이슈",
                total=len(details),
                data=RecentIssueWidgetData(issue_details=list(details)),
            )
        },
    )


class SlaDashboardUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.jira = FakeJira()
        self.reports = FakeReports(
            latest_report(
                recent_detail("TACEA-4501"),
                recent_detail("TACEA-4500", status="이슈 리뷰 중"),
                recent_detail("OTHER-1"),
            )
        )
        self.use_case = SlaDashboardUseCase(
            reports=self.reports,
            jira=self.jira,
            project_key="TACEA",
        )

    async def test_lists_latest_report_issues_with_live_activity_fields(self) -> None:
        self.jira.issues = [
            {
                "key": "TACEA-4501",
                "fields": {
                    "created": "2026-08-20T09:10:11.000+0900",
                    "updated": "2026-08-21T14:15:16.000+0900",
                    "status": {"name": "구현 중"},
                },
            }
        ]

        issues = await self.use_case.list_recent_issues()

        self.assertEqual(["TACEA-4501", "TACEA-4500"], [issue.key for issue in issues])
        self.assertEqual("2026-08-20 09:10", issues[0].created)
        self.assertEqual("2026-08-21 14:15", issues[0].updated)
        self.assertEqual("구현 중", issues[0].status)
        self.assertEqual("2026-08-20 09:00", issues[1].created)
        self.assertEqual("", issues[1].updated)
        self.assertEqual("이슈 리뷰 중", issues[1].status)
        self.assertEqual(
            (
                "issuekey IN (TACEA-4501, TACEA-4500) ORDER BY issuekey DESC",
                500,
                "created,updated,status",
            ),
            self.jira.issue_requests[0],
        )

    async def test_returns_five_newest_comments_and_flattens_adf(self) -> None:
        self.jira.comments = [
            {
                "id": str(index),
                "author": {"displayName": f"작성자 {index}"},
                "body": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": f"댓글 {index}"},
                                {"type": "hardBreak"},
                                {"type": "mention", "attrs": {"text": "@담당자"}},
                            ],
                        }
                    ],
                },
                "created": f"2026-08-{index + 10:02d}T10:00:00.000+0900",
                "updated": f"2026-08-{index + 10:02d}T11:00:00.000+0900",
            }
            for index in range(6)
        ]

        comments = await self.use_case.list_recent_comments("tacea-4501")

        self.assertEqual(["5", "4", "3", "2", "1"], [comment.id for comment in comments])
        self.assertEqual("댓글 5\n@담당자", comments[0].body)
        self.assertEqual("작성자 5", comments[0].author)
        self.assertEqual("2026-08-15 10:00", comments[0].created)
        self.assertEqual([("TACEA-4501", 5)], self.jira.comment_requests)

    async def test_rejects_comment_lookup_outside_latest_issue_set(self) -> None:
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.list_recent_comments("TACEA-9999")

        self.assertEqual([], self.jira.comment_requests)
