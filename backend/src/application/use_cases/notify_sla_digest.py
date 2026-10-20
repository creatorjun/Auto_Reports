# backend/src/application/use_cases/notify_sla_digest.py
import asyncio
import logging
from datetime import date, datetime

from src.application.ports.email_port import EmailPort
from src.application.ports.sla_digest_port import SlaDigestRendererPort, SlaDigestSourcePort
from src.domain.constants import KST


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

    async def execute(self, now: datetime | None = None) -> int:
        async with self._lock:
            current = now if now is not None else datetime.now(KST)
            current = current.replace(tzinfo=KST) if current.tzinfo is None else current.astimezone(KST)
            if not self._notify_to or self._last_sent_date == current.date():
                return 0

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
            if not entries:
                logger.info("[SlaDigest] 발송 대상 없음")
                return 0

            ticket_count = len({entry.key for entry in entries})
            body = self._renderer.render(entries, self._jira_base_url, current)
            await self._email.send(
                to=self._notify_to,
                subject=f"[TAC] SLA 일일 알림 {current:%Y-%m-%d} — {ticket_count}건",
                body=body,
            )
            self._last_sent_date = current.date()
            logger.info("[SlaDigest] 티켓 %d건, SLA %d건 발송 완료", ticket_count, len(entries))
            return ticket_count
