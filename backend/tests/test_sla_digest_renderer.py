# backend/tests/test_sla_digest_renderer.py
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from html import escape
from urllib.parse import quote

from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestEntry
from src.presentation.email.sla_digest_renderer import SlaDigestRenderer


NOW = datetime(2026, 10, 20, 9, tzinfo=KST)
ENTRY = SlaDigestEntry(
    key="TAC-1", summary="원격 지원", status="처리 중", assignee="담당자",
    sla_id="12", sla_name="처리 중", goal_millis=36000000, remaining_millis=10800000,
)


class SlaDigestRendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = SlaDigestRenderer()

    def test_groups_all_stages_and_shows_ticket_counts_and_sla_durations(self) -> None:
        body = self.renderer.render(
            (ENTRY, replace(ENTRY, sla_id="13", sla_name="결과 대기 중", remaining_millis=60000, paused=True)),
            "https://jira.example.test/jira/", NOW,
        )

        self.assertIn("티켓 1건", body)
        self.assertIn("SLA 2건", body)
        self.assertIn('aria-label="처리 중"', body)
        self.assertIn('aria-label="결과 대기 중"', body)
        self.assertEqual(2, body.count('href="https://jira.example.test/jira/browse/TAC-1"'))
        self.assertIn("10시간 0분 0초", body)
        self.assertIn("잔여 3시간 0분 0초", body)
        self.assertIn("30.0%", body)
        self.assertIn('color:#dc2626;font-weight:700;\">잔여 3시간 0분 0초</span>', body)
        self.assertIn('color:#dc2626;font-weight:700;\">30.0%</span>', body)
        self.assertIn('color:#dc2626;\">잔여 시간</th>', body)
        self.assertIn('color:#dc2626;\">잔여율</th>', body)
        self.assertIn("잔여 1분 0초", body)
        self.assertIn("0.2%", body)
        self.assertIn("일시정지", body)
        self.assertIn("SLA 위반 이력이 없는 티켓만 포함", body)
        self.assertIn("2026-10-20 09:00 KST", body)

    def test_jira_text_and_issue_url_are_escaped(self) -> None:
        unsafe = '<script>alert("x")</script> & \'y\''
        issue = replace(ENTRY, key="TAC-1/../?a='x'&b=\"y\"#z", summary=unsafe, status=unsafe, assignee=unsafe, sla_name=unsafe)

        body = self.renderer.render((issue,), "https://jira.example.test", NOW)

        self.assertNotIn("<script>", body)
        self.assertIn(escape(unsafe), body)
        self.assertIn(f'href="https://jira.example.test/browse/{quote(issue.key, safe="")}"', body)
        self.assertIn(escape(issue.key), body)
        self.assertIn(f'aria-label="{escape(unsafe, quote=True)}"', body)

    def test_invalid_or_unsafe_base_urls_are_rejected(self) -> None:
        for value in (
            "javascript:alert(1)", "data:text/html,test", "//jira.example.test",
            "https://", "https://user:pass@jira.example.test", "https://jira.example.test?x=1",
            "https://jira.example.test#fragment", "https://jira.example.test\n/browse",
            "https://jira.example.test\\evil", "https://jira.example.test:bad",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.renderer.render((ENTRY,), value, NOW)

    def test_timezone_conversion_and_unassigned_and_zero_remaining(self) -> None:
        body = self.renderer.render(
            (replace(ENTRY, assignee="", remaining_millis=0),), "https://jira.example.test",
            datetime(2026, 10, 20, 0, tzinfo=timezone.utc),
        )

        self.assertIn("2026-10-20 09:00 KST", body)
        self.assertIn("미지정", body)
        self.assertIn("잔여 0초", body)
        self.assertIn("0.0%", body)

    def test_under_one_second_is_not_rendered_as_zero(self) -> None:
        body = self.renderer.render((replace(ENTRY, remaining_millis=1),), "https://jira.example.test", NOW)

        self.assertIn("잔여 1초 미만", body)
