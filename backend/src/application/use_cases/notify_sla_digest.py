# backend/src/application/use_cases/notify_sla_digest.py
import asyncio
import logging
from datetime import date, datetime

from src.application.ports.email_port import EmailPort
from src.application.ports.sla_digest_port import SlaDigestRendererPort, SlaDigestSourcePort
from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestResult


logger = logging.getLogger(__name__)


class NotifySlaDigestUseCase:
    def __init__(
        self,
        source: SlaDigestSourcePort,
        email: EmailPort,
        renderer: SlaDigestRendererPort,
        notify_to: list[str],
        jira_base_url: str,
    ) -> None:
        self._source = source
        self._email = email
        self._renderer = renderer
        self._notify_to = list(dict.fromkeys(address.strip() for address in notify_to if address.strip()))
        self._jira_base_url = jira_base_url
        self._lock = asyncio.Lock()
        self._last_sent_date: date | None = None
        self._last_sent_counts = (0, 0)

    async def execute(self, now: datetime | None = None) -> int:
        result = await self.trigger(now=now)
        return result.ticket_count if result.status == "sent" else 0

    async def trigger(self, dry_run: bool = False, now: datetime | None = None) -> SlaDigestResult:
        async with self._lock:
            current = now if now is not None else datetime.now(KST)
            current = current.replace(tzinfo=KST) if current.tzinfo is None else current.astimezone(KST)
            recipient_count = len(self._notify_to)
            if not recipient_count:
                return SlaDigestResult("preview" if dry_run else "no_matches", 0, 0, 0, current)
            if not dry_run and self._last_sent_date == current.date():
                return SlaDigestResult("already_sent", *self._last_sent_counts, recipient_count, current)

            candidates = await self._source.fetch_entries()
            breached_keys = {
                entry.key for entry in candidates
                if entry.issue_has_breached_sla or entry.breached or entry.remaining_millis < 0
            }
            entries = tuple(
                entry for entry in candidates
                if entry.key not in breached_keys
                and entry.goal_millis > 0
                and entry.remaining_millis * 100 <= entry.goal_millis * 30
            )
            ticket_count = len({entry.key for entry in entries})
            sla_count = len(entries)
            if dry_run:
                return SlaDigestResult("preview", ticket_count, sla_count, recipient_count, current)
            if not entries:
                logger.info("[SlaDigest] 발송 대상 없음")
                return SlaDigestResult("no_matches", 0, 0, recipient_count, current)

            body = self._renderer.render(entries, self._jira_base_url, current)
            await self._email.send(
                to=self._notify_to,
                subject=f"[TAC] SLA 일일 알림 {current:%Y-%m-%d} — {ticket_count}건",
                body=body,
            )
            self._last_sent_date = current.date()
            self._last_sent_counts = (ticket_count, sla_count)
            logger.info("[SlaDigest] 티켓 %d건, SLA %d건 발송 완료", ticket_count, sla_count)
            return SlaDigestResult("sent", ticket_count, sla_count, recipient_count, current)
