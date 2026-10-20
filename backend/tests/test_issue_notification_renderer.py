# backend/tests/test_issue_notification_renderer.py
import hashlib
import unittest
from dataclasses import replace
from datetime import datetime
from html import escape
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import quote

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
    def test_tac_assigned_html_contract_is_preserved(self) -> None:
        renderer = IssueNotificationRenderer()
        body = renderer.render_tac_assigned(issue(), JIRA_URL, NOW)
        self.assertEqual(
            "1aa6143c066efd5cb7a188fb961c3be1c42b9a1435352f449cfdda538c498e2f",
            hashlib.sha256(body.encode()).hexdigest(),
        )

    def test_todo_layout_preserves_columns_ticket_information_and_summary_limit(self) -> None:
        entry = issue()
        entries = [entry, replace(entry, key="TACEA-43", summary="고객 시스템 점검", type="인시던트")]
        body = IssueNotificationRenderer().render_todo(entries, f"{JIRA_URL}/jira/", NOW)

        for label in ("이슈 번호", "요약", "유형", "생성일"):
            self.assertIn(f">{label}</th>", body)
        for value in (
            "TAC AUTO REPORTS", "할 일 이슈 알림", "총 2건", "2026-10-06 09:15 KST",
            "2026-10-01 09:30", "TACEA-42", entry.summary[:80], "개선", "고객 시스템 점검", "인시던트",
        ):
            self.assertIn(value, body)
        self.assertNotIn(entry.summary, body)
        self.assertIn('href="https://jira.example.test/jira/browse/TACEA-42"', body)
        self.assertIn('href="https://jira.example.test/jira/browse/TACEA-43"', body)
        self.assertLess(body.index("TACEA-42"), body.index("TACEA-43"))
        self.assertIn("background:#f8fafc", body)
        self.assertIn("background:#ffffff", body)
        self.assertIn('scope="col"', body)

    def test_todo_escapes_all_issue_text_and_encodes_ticket_links(self) -> None:
        entry = replace(
            issue(), key='TAC-1/../?a="x"&b=\'y\'#z', summary='<script>alert("x")</script> & \'summary\'',
            type='<img src=x onerror="alert(1)">', created='<svg onload="1">',
        )
        body = IssueNotificationRenderer().render_todo([entry], JIRA_URL, NOW)

        for value in (entry.key, entry.summary[:80], entry.type, entry.created[:16].replace("T", " ")):
            self.assertIn(escape(value), body)
        self.assertNotIn("<script>", body)
        self.assertNotIn("<img src=", body)
        self.assertNotIn("<svg onload=", body)
        self.assertIn(f'href="{JIRA_URL}/browse/{quote(entry.key, safe="")}"', body)

    def test_todo_rejects_unsafe_or_malformed_jira_base_urls(self) -> None:
        for base_url in (
            "javascript:alert(1)", "data:text/html,test", "//jira.example.test", "https://",
            "https://user:password@jira.example.test", "https://jira.example.test?next=elsewhere",
            "https://jira.example.test#fragment", "https://jira.example.test\n/browse",
            "https://jira.example.test\\other", "https://jira.example.test:bad",
        ):
            with self.subTest(base_url=base_url), self.assertRaises(ValueError):
                IssueNotificationRenderer().render_todo([issue()], base_url, NOW)

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
