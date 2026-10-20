# backend/src/presentation/email/sla_digest_renderer.py
from collections import defaultdict
from datetime import datetime
from html import escape
from urllib.parse import quote, urlsplit

from src.application.ports.sla_digest_port import SlaDigestRendererPort
from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestEntry


CELL_STYLE = "padding:12px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top;"
REMAINING_COLOR = "#dc2626"


def _safe_base_url(value: str) -> str:
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("Jira base URL must be an HTTP(S) URL without whitespace")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
    ):
        raise ValueError("Jira base URL must be an HTTP(S) URL without credentials, query or fragment")
    parsed.port
    return value.rstrip("/")


def _duration(millis: int) -> str:
    total_seconds = abs(millis) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:,}시간 {minutes}분 {seconds}초"
    if minutes:
        return f"{minutes}분 {seconds}초"
    if abs(millis) < 1000 and millis != 0:
        return "1초 미만"
    return f"{seconds}초"


def _row(entry: SlaDigestEntry, jira_base_url: str) -> str:
    url = escape(f"{jira_base_url}/browse/{quote(entry.key, safe='')}", quote=True)
    remaining = f"잔여 {_duration(entry.remaining_millis)}"
    percentage = f"{entry.remaining_millis * 100 / entry.goal_millis:.1f}%" if entry.goal_millis > 0 else "산정 불가"
    state = "일시정지" if entry.paused else "진행 중"
    cells = (
        f"<a href=\"{url}\" style=\"color:#2563eb;font-weight:700;text-decoration:none;\">{escape(entry.key)}</a>",
        escape(entry.summary),
        escape(entry.status),
        escape(entry.assignee or "미지정"),
        _duration(entry.goal_millis),
        f"<span style=\"color:{REMAINING_COLOR};font-weight:700;\">{remaining}</span>",
        f"<span style=\"color:{REMAINING_COLOR};font-weight:700;\">{percentage}</span>",
        state,
    )
    return "<tr>" + "".join(f"<td style=\"{CELL_STYLE}\">{cell}</td>" for cell in cells) + "</tr>"


class SlaDigestRenderer(SlaDigestRendererPort):
    def render(
        self, entries: tuple[SlaDigestEntry, ...], jira_base_url: str, now: datetime,
    ) -> str:
        base_url = _safe_base_url(jira_base_url)
        current = now.replace(tzinfo=KST) if now.tzinfo is None else now.astimezone(KST)
        groups: dict[tuple[str, str], list[SlaDigestEntry]] = defaultdict(list)
        for entry in entries:
            groups[(entry.sla_id, entry.sla_name)].append(entry)
        sections = []
        labels = ("티켓", "제목", "현재 상태", "담당자", "목표 시간", "잔여 시간", "잔여율", "진행 상태")
        headings = "".join(
            f"<th scope=\"col\" style=\"{CELL_STYLE}font-weight:600;"
            f"color:{REMAINING_COLOR if label in {'잔여 시간', '잔여율'} else '#475569'};\">{label}</th>"
            for label in labels
        )
        for (sla_id, name), group in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
            rows = "".join(
                _row(entry, base_url)
                for entry in sorted(group, key=lambda item: (item.remaining_millis, item.key))
            )
            count = len({entry.key for entry in group})
            sections.append(
                f"<section style=\"margin-top:28px;\">"
                f"<h2 style=\"font-size:17px;margin:0 0 12px;color:#0f172a;\">{escape(name)}"
                f" <span style=\"font-size:13px;font-weight:400;color:#64748b;\">{count}건</span></h2>"
                f"<table aria-label=\"{escape(name, quote=True)}\" style=\"width:100%;border-collapse:collapse;font-size:13px;background:#ffffff;\">"
                f"<thead style=\"background:#f1f5f9;\"><tr>{headings}</tr></thead><tbody>{rows}</tbody></table></section>"
            )
        ticket_count = len({entry.key for entry in entries})
        return (
            "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"></head>"
            "<body style=\"margin:0;background:#f8fafc;color:#0f172a;font-family:Arial,'Malgun Gothic',sans-serif;\">"
            "<main style=\"padding:28px;max-width:1280px;margin:auto;\">"
            "<div style=\"font-size:12px;font-weight:700;letter-spacing:1px;color:#2563eb;\">TAC AUTO REPORTS</div>"
            "<h1 style=\"font-size:26px;margin:10px 0 12px;\">SLA 위반 임박 일일 알림</h1>"
            f"<p style=\"margin:0;color:#475569;\">{current:%Y-%m-%d %H:%M} KST 기준 · "
            f"<strong>티켓 {ticket_count}건</strong> · SLA {len(entries)}건</p>"
            "<p style=\"padding:14px 16px;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;font-size:14px;line-height:1.6;\">"
            "진행 중인 SLA의 목표 시간 대비 잔여 시간이 <strong>30% 이하</strong>인 티켓입니다. "
            "SLA 위반 이력이 없는 티켓만 포함하며, 일시정지 상태는 별도로 표시합니다. 시간은 Jira SLA 업무시간 기준이며, "
            "동일 티켓이 여러 단계에 해당하면 각 단계에 표시됩니다.</p>"
            + "".join(sections)
            + "<p style=\"margin-top:28px;font-size:12px;color:#64748b;\">TAC Auto Reports · 매일 09:00 KST 자동 알림</p>"
            "</main></body></html>"
        )
