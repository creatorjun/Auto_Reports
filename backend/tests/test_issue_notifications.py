# backend/tests/test_issue_notifications.py
import pathlib
import sys
import unittest
from unittest.mock import AsyncMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.email_port import EmailPort
from src.application.use_cases.notify_tac_assigned import NotifyTacAssignedUseCase, extract_tac_assigned_issues
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase, extract_todo_issues
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId


LICENSE_ALIASES = ("라이선스", "라이센스", "라이선스 요청", "라이센스 요청", " 라이센스 ")


def recent_issue(key: str, issue_type: str, status: str = "할 일", tac_team: str = "담당자 A") -> RecentIssueDetail:
    return RecentIssueDetail(
        key=key, summary=f"{key} 확인", type=issue_type, status=status,
        stage_index=0, created="2026-09-10 09:00", elapsed_days=0, tac_team=tac_team,
    )


def widgets_with(*issues: RecentIssueDetail) -> dict[WidgetId, WidgetResult]:
    return {WidgetId.RECENT_ISSUES: WidgetResult(
        name="최근 이슈", total=len(issues), data=RecentIssueWidgetData(list(issues)),
    )}


class IssueNotificationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.email = AsyncMock(spec=EmailPort)
        self.todo = NotifyTodoIssuesUseCase(self.email, ["test@example.test"], "https://jira.example.test")
        self.tac = NotifyTacAssignedUseCase(
            self.email, ["test@example.test"], "https://jira.example.test", keyword="담당자 A",
        )

    async def test_license_only_todo_issues_never_send_email(self):
        for alias in LICENSE_ALIASES:
            with self.subTest(alias=alias):
                widgets = widgets_with(recent_issue("LICENSE-1", alias))
                selected = extract_todo_issues(widgets)

                await self.todo.execute(selected)

                self.assertEqual([], selected)
                self.assertEqual(1, widgets[WidgetId.RECENT_ISSUES].total)
                self.email.send.assert_not_awaited()

    async def test_license_only_tac_assignments_never_send_email(self):
        for alias in LICENSE_ALIASES:
            with self.subTest(alias=alias):
                widgets = widgets_with(recent_issue("LICENSE-1", alias))

                await self.tac.execute(widgets)

                self.assertEqual([], extract_tac_assigned_issues(widgets, "담당자 A"))
                self.assertEqual(1, widgets[WidgetId.RECENT_ISSUES].total)
                self.email.send.assert_not_awaited()

    async def test_todo_notifications_keep_normal_status_filtering_and_deduplication(self):
        widgets = widgets_with(
            recent_issue("ISSUE-1", "인시던트"),
            recent_issue("ISSUE-2", "개선", status="재오픈"),
            recent_issue("IN-PROGRESS", "인시던트", status="처리 중"),
            *(recent_issue(f"LICENSE-{index}", alias) for index, alias in enumerate(LICENSE_ALIASES)),
        )
        selected = extract_todo_issues(widgets)

        await self.todo.execute(selected)
        await self.todo.execute(selected)

        self.assertEqual(["ISSUE-1", "ISSUE-2"], [issue.key for issue in selected])
        self.email.send.assert_awaited_once()
        message = self.email.send.await_args.kwargs
        self.assertEqual("[TAC] 할일 이슈: ISSUE-1, ISSUE-2", message["subject"])
        self.assertNotIn("LICENSE-", message["body"])
        self.assertNotIn("IN-PROGRESS", message["body"])

    async def test_tac_notifications_keep_normal_assignee_matching_and_deduplication(self):
        widgets = widgets_with(
            recent_issue("ISSUE-1", "인시던트", status="처리 중"),
            recent_issue("OTHER-TEAM", "개선", tac_team="담당자 B"),
            *(recent_issue(f"LICENSE-{index}", alias) for index, alias in enumerate(LICENSE_ALIASES)),
        )

        await self.tac.execute(widgets)
        await self.tac.execute(widgets)

        self.assertEqual(["ISSUE-1"], [issue.key for issue in extract_tac_assigned_issues(widgets, "담당자 A")])
        self.email.send.assert_awaited_once()
        message = self.email.send.await_args.kwargs
        self.assertIn("ISSUE-1", message["subject"])
        self.assertNotIn("LICENSE-", message["body"])
        self.assertNotIn("OTHER-TEAM", message["body"])
