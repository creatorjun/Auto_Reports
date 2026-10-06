# backend/tests/test_issue_notification_renderer.py
import hashlib
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from src.application.ports.email_port import EmailPort
from src.application.ports.issue_notification_renderer_port import IssueNotificationRendererPort
from src.application.use_cases.notify_tac_assigned import NotifyTacAssignedUseCase
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase
from src.domain.constants import KST
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.presentation.email.issue_notification_renderer import IssueNotificationRenderer


NOW = datetime(2026, 10, 6, 9, 15, tzinfo=KST)
JIRA_URL = "https://jira.example.test"


def issue() -> RecentIssueDetail:
    return RecentIssueDetail(
        key="TACEA-42", summary="가나다" * 40, type="개선", status="재오픈",
        stage_index=0, created="2026-10-01T09:30:00+09:00", elapsed_days=5,
        tac_team="담당자 A",
    )


class IssueNotificationRendererTest(unittest.IsolatedAsyncioTestCase):
    def test_existing_html_contract_is_preserved(self) -> None:
        renderer = IssueNotificationRenderer()
        messages = (
            (renderer.render_todo([issue()], JIRA_URL, NOW), "10fff38d8a239091004ad2d348904719605908983e4d6a79fe589f2d0e52b4dc"),
            (renderer.render_tac_assigned(issue(), JIRA_URL, NOW), "1aa6143c066efd5cb7a188fb961c3be1c42b9a1435352f449cfdda538c498e2f"),
        )
        for body, expected in messages:
            with self.subTest(expected=expected):
                self.assertEqual(expected, hashlib.sha256(body.encode()).hexdigest())

    async def test_use_cases_send_the_injected_renderers_body(self) -> None:
        for kind in ("todo", "tac_assigned"):
            with self.subTest(kind=kind):
                email = AsyncMock(spec=EmailPort)
                renderer = Mock(spec=IssueNotificationRendererPort)
                render = getattr(renderer, f"render_{kind}")
                render.return_value = "rendered by another adapter"
                entry = issue()
                if kind == "todo":
                    use_case = NotifyTodoIssuesUseCase(email, ["test@example.test"], JIRA_URL, renderer)
                    payload = [entry]
                    render_payload = payload
                else:
                    use_case = NotifyTacAssignedUseCase(email, ["test@example.test"], JIRA_URL, renderer, keyword="담당자 A")
                    payload = {WidgetId.RECENT_ISSUES: WidgetResult(
                        name="최근 이슈", total=1, data=RecentIssueWidgetData([entry]),
                    )}
                    render_payload = entry
                with patch(f"src.application.use_cases.notify_{kind if kind == 'tac_assigned' else 'todo_issues'}.datetime") as clock:
                    clock.now.return_value = NOW
                    await use_case.execute(payload)
                    await use_case.execute(payload)
                render.assert_called_once_with(render_payload, JIRA_URL, NOW)
                email.send.assert_awaited_once()
                self.assertEqual("rendered by another adapter", email.send.await_args.kwargs["body"])

    async def test_render_and_delivery_failures_allow_retry(self) -> None:
        for kind in ("todo", "tac_assigned"):
            for phase in ("render", "delivery"):
                with self.subTest(kind=kind, phase=phase):
                    email = AsyncMock(spec=EmailPort)
                    renderer = Mock(spec=IssueNotificationRendererPort)
                    render = getattr(renderer, f"render_{kind}")
                    render.return_value = "retry body"
                    if kind == "todo":
                        use_case = NotifyTodoIssuesUseCase(email, ["test@example.test"], JIRA_URL, renderer)
                        payload = [issue()]
                    else:
                        use_case = NotifyTacAssignedUseCase(email, ["test@example.test"], JIRA_URL, renderer, keyword="담당자 A")
                        payload = {WidgetId.RECENT_ISSUES: WidgetResult(
                            name="최근 이슈", total=1, data=RecentIssueWidgetData([issue()]),
                        )}
                    operation = render if phase == "render" else email.send
                    operation.side_effect = RuntimeError("adapter failed")
                    with self.assertRaisesRegex(RuntimeError, "adapter failed"):
                        await use_case.execute(payload)
                    operation.side_effect = None
                    await use_case.execute(payload)
                    await use_case.execute(payload)
                    self.assertEqual(2, render.call_count)
                    self.assertEqual(1 if phase == "render" else 2, email.send.await_count)
