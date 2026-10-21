# backend/src/application/use_cases/sla_status.py
import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from fractions import Fraction
from time import monotonic

from src.application.ports.sla_digest_port import SlaDigestSourcePort
from src.application.ports.sla_status_port import SlaStatusDetailsPort
from src.application.ports.sla_status_snapshot_port import SlaStatusSnapshotPort
from src.application.services.sla_violation_metrics import build_sla_ticket
from src.domain.constants import KST
from src.domain.entities.sla_digest import SlaDigestEntry
from src.domain.entities.sla_status import SlaStatusMetric, SlaStatusSnapshot, SlaStatusTicket
from src.domain.entities.sla_violation_report import SlaViolationIssue
from src.domain.services.issue_type_policy import is_license_issue_type


class SlaStatusSourceError(RuntimeError):
    pass


@dataclass
class _SnapshotFlight:
    task: asyncio.Task[SlaStatusSnapshot]
    background: bool = False
    waiters: int = 0


def _snapshot(entries: tuple[SlaDigestEntry, ...], generated_at: datetime) -> SlaStatusSnapshot:
    breached_keys = {
        entry.key for entry in entries
        if entry.issue_has_breached_sla or entry.breached or entry.remaining_millis < 0
    }
    latest = {(entry.key, entry.sla_id): entry for entry in entries}
    grouped: dict[str, list[SlaDigestEntry]] = {}
    for entry in latest.values():
        if (
            entry.key not in breached_keys
            and entry.goal_millis > 0
            and entry.remaining_millis >= 0
            and entry.remaining_millis * 100 < entry.goal_millis * 30
        ):
            grouped.setdefault(entry.key, []).append(entry)
    tickets = []
    for key, qualifying in grouped.items():
        qualifying.sort(key=lambda entry: (
            Fraction(entry.remaining_millis, entry.goal_millis), entry.remaining_millis, entry.sla_id,
        ))
        details = qualifying[0]
        tickets.append(SlaStatusTicket(
            key=key, summary=details.summary, status=details.status, assignee=details.assignee,
            slas=tuple(SlaStatusMetric(
                sla_id=entry.sla_id, sla_name=entry.sla_name, goal_millis=entry.goal_millis,
                remaining_millis=entry.remaining_millis,
                remaining_percent=entry.remaining_millis * 100 / entry.goal_millis,
                paused=entry.paused,
            ) for entry in qualifying),
            warnings=("상세 상태 이력을 수집하지 않아 상태별 체류시간을 확인할 수 없습니다.",),
        ))
    tickets.sort(key=lambda ticket: (
        Fraction(ticket.slas[0].remaining_millis, ticket.slas[0].goal_millis),
        ticket.slas[0].remaining_millis, ticket.key,
    ))
    return SlaStatusSnapshot(
        generated_at=generated_at, threshold_percent=30, ticket_count=len(tickets),
        sla_count=sum(len(ticket.slas) for ticket in tickets), tickets=tuple(tickets),
    )


def _with_details(
    snapshot: SlaStatusSnapshot, issues: tuple[SlaViolationIssue, ...], generated_at: datetime,
) -> SlaStatusSnapshot:
    breached_keys = {
        issue.key for issue in issues
        if any(cycle.breached or (
            cycle.ongoing and cycle.goal_ms is not None and cycle.elapsed_ms is not None
            and cycle.elapsed_ms > cycle.goal_ms
        ) for cycle in issue.cycles)
    }
    by_key = {issue.key: issue for issue in issues}
    tickets = []
    for ticket in snapshot.tickets:
        issue = by_key.get(ticket.key)
        if issue is None or issue.key in breached_keys or is_license_issue_type(issue.issue_type or ""):
            continue
        detailed = build_sla_ticket(issue, generated_at)
        tickets.append(replace(
            ticket, summary=detailed.summary, status=detailed.current_status,
            assignee=detailed.assignee or "미지정", created_at=detailed.created_at,
            elapsed_days=detailed.elapsed_days, customer=detailed.customer,
            partners=detailed.partners, reporter=detailed.reporter,
            tac_assignee=detailed.tac_assignee, issue_type=detailed.issue_type,
            status_durations=detailed.status_durations, status_durations_basis="resolution_sla",
            status_duration_calendar=detailed.status_duration_calendar, warnings=detailed.warnings,
            reporter_account_id=detailed.reporter_account_id,
            assignee_account_id=detailed.assignee_account_id,
            tac_assignee_account_id=detailed.tac_assignee_account_id,
            personal_data_retrieved_at=detailed.personal_data_retrieved_at,
            personal_data_field_retrieved_at=detailed.personal_data_field_retrieved_at,
        ))
    return replace(
        snapshot, generated_at=generated_at, tickets=tuple(tickets), ticket_count=len(tickets),
        sla_count=sum(len(ticket.slas) for ticket in tickets),
    )


class SlaStatusUseCase:
    def __init__(
        self,
        source: SlaDigestSourcePort,
        details: SlaStatusDetailsPort | None = None,
        cache_seconds: float = 60,
        clock: Callable[[], float] = monotonic,
        now: Callable[[], datetime] | None = None,
        timeout_seconds: float = 110,
        snapshots: SlaStatusSnapshotPort | None = None,
        project_key: str = "TACEA",
    ) -> None:
        if cache_seconds < 0:
            raise ValueError("SLA status cache duration must be nonnegative")
        if timeout_seconds <= 0:
            raise ValueError("SLA status collection timeout must be positive")
        self._source = source
        self._details = details
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._now = now
        self._timeout_seconds = timeout_seconds
        self._snapshots = snapshots
        self._project_key = project_key
        self._restored = snapshots is None
        self._restore_lock = asyncio.Lock()
        self._cached: SlaStatusSnapshot | None = None
        self._cached_at = 0.0
        self._flight: _SnapshotFlight | None = None
        self._closed = False
        self._generation = 0
        self._refresh_error: str | None = None
        self._retry_after = 0.0

    async def initialize(self) -> None:
        if self._restored:
            return
        async with self._restore_lock:
            if self._restored or self._closed:
                return
            generation = self._generation
            try:
                snapshot = await self._snapshots.load(self._project_key)
            except Exception as error:
                raise SlaStatusSourceError("Stored SLA status could not be loaded") from error
            if generation != self._generation or self._closed:
                return
            if snapshot is not None:
                self._cached = replace(snapshot, refresh_in_progress=False, stale=False, refresh_error=None)
                age = max(0.0, (self._generated_at() - snapshot.generated_at).total_seconds())
                self._cached_at = self._clock() - age
            self._restored = True

    async def get_snapshot(self, refresh: bool = False) -> SlaStatusSnapshot:
        if self._closed:
            raise SlaStatusSourceError("SLA status is closed")
        await self.initialize()
        if self._closed:
            raise SlaStatusSourceError("SLA status is closed")
        flight = self._flight
        if flight is None or flight.task.done():
            if self._cached is not None and not refresh and (
                self._clock() - self._cached_at < self._cache_seconds or self._clock() < self._retry_after
            ):
                return self._response()
            self._refresh_error = None
            flight = _SnapshotFlight(
                asyncio.create_task(self._load(self._generation)), background=self._cached is not None,
            )
            flight.task.add_done_callback(self._finish)
            self._flight = flight
        if self._cached is not None:
            return self._response()
        flight.waiters += 1
        try:
            return await asyncio.shield(flight.task)
        finally:
            flight.waiters -= 1
            if flight.waiters == 0 and not flight.background:
                if self._flight is flight:
                    self._flight = None
                if not flight.task.done():
                    flight.task.cancel()
                    await asyncio.gather(flight.task, return_exceptions=True)

    def _finish(self, task: asyncio.Task[SlaStatusSnapshot]) -> None:
        if not task.cancelled():
            task.exception()
        if self._flight is not None and self._flight.task is task:
            self._flight = None

    def _response(self) -> SlaStatusSnapshot:
        refreshing = self._flight is not None and not self._flight.task.done()
        stale = self._clock() - self._cached_at >= self._cache_seconds or self._refresh_error is not None
        if not refreshing and not stale and self._refresh_error is None:
            return self._cached
        return replace(self._cached, refresh_in_progress=refreshing, stale=stale, refresh_error=self._refresh_error)

    async def _load(self, generation: int) -> SlaStatusSnapshot:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                entries = await self._source.fetch_entries()
                snapshot = _snapshot(entries, self._generated_at())
                if self._details is not None and snapshot.tickets:
                    issues = await self._details.fetch_details(tuple(ticket.key for ticket in snapshot.tickets))
                    snapshot = _with_details(snapshot, issues, self._generated_at())
                if self._closed or generation != self._generation:
                    raise SlaStatusSourceError("SLA status collection was invalidated")
                if self._snapshots is not None:
                    snapshot = await self._snapshots.save(self._project_key, snapshot)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if generation == self._generation and not self._closed:
                self._refresh_error = "최신 SLA 현황을 불러오지 못했습니다. 마지막으로 저장된 현황을 표시합니다."
                self._retry_after = self._clock() + max(self._cache_seconds, 30)
            raise SlaStatusSourceError("Jira SLA status collection failed") from error
        if self._closed or generation != self._generation:
            raise SlaStatusSourceError("SLA status collection was invalidated")
        self._cached = snapshot
        self._cached_at = self._clock()
        self._refresh_error = None
        self._retry_after = 0.0
        return snapshot

    def _generated_at(self) -> datetime:
        value = self._now() if self._now is not None else datetime.now(KST)
        return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)

    async def clear_personal_data_cache(self) -> None:
        self._generation += 1
        self._cached = None
        self._cached_at = 0.0
        self._restored = self._snapshots is None
        self._refresh_error = None
        self._retry_after = 0.0
        flight = self._flight
        self._flight = None
        if flight is not None and not flight.task.done():
            flight.task.cancel()
            await asyncio.gather(flight.task, return_exceptions=True)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.clear_personal_data_cache()
