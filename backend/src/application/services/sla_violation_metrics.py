# backend/src/application/services/sla_violation_metrics.py
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from src.domain.constants import KST
from src.application.services.sla_status_clock import calculate_sla_status_durations
from src.domain.entities.sla_violation_report import (
    SlaViolationBreach,
    SlaViolationIssue,
    SlaViolationPeriod,
    SlaViolationReport,
    SlaViolationTicket,
)


def sla_violation_window(period: SlaViolationPeriod, selected_date: date) -> tuple[datetime, datetime]:
    if period == "week":
        start_date = selected_date - timedelta(days=selected_date.weekday())
        end_date = selected_date + timedelta(days=1)
    elif period == "month":
        start_date = selected_date.replace(day=1)
        end_date = date(start_date.year + 1, 1, 1) if start_date.month == 12 else date(start_date.year, start_date.month + 1, 1)
    elif period == "year":
        start_date = date(selected_date.year, 1, 1)
        end_date = date(selected_date.year + 1, 1, 1)
    else:
        raise ValueError("집계 기간은 week, month, year 중 하나여야 합니다.")
    return datetime.combine(start_date, time.min, KST), datetime.combine(end_date, time.min, KST)


def _local(value: datetime) -> datetime:
    return value.replace(tzinfo=KST) if value.tzinfo is None else value.astimezone(KST)


def _timeline(issue: SlaViolationIssue, as_of: datetime) -> list[tuple[datetime, datetime, str]]:
    if not issue.history_complete:
        raise ValueError("상태 이력이 불완전하여 위반 당시 상태와 체류시간을 확인할 수 없습니다.")
    created = _local(issue.created_at)
    ordered = sorted(issue.changes, key=lambda change: _local(change.changed_at))
    status = ordered[0].from_status if ordered else issue.current_status
    if not status or not issue.current_status:
        raise ValueError("티켓 상태가 누락되어 상태별 체류시간을 확인할 수 없습니다.")
    intervals: list[tuple[datetime, datetime, str]] = []
    cursor = created
    for change in ordered:
        changed_at = _local(change.changed_at)
        if changed_at < cursor or changed_at > as_of or change.from_status != status or not change.to_status:
            raise ValueError("상태 이력의 연속성 또는 시각이 유효하지 않아 위반 당시 상태와 체류시간을 확인할 수 없습니다.")
        intervals.append((cursor, changed_at, status))
        cursor, status = changed_at, change.to_status
    if status != issue.current_status:
        raise ValueError("마지막 상태 이력과 현재 상태가 달라 위반 당시 상태와 체류시간을 확인할 수 없습니다.")
    intervals.append((cursor, as_of, status))
    return intervals


def _ticket(issue: SlaViolationIssue, generated_at: datetime) -> SlaViolationTicket:
    warnings = list(issue.warnings)
    intervals = None
    durations = None
    calendar_name = None
    try:
        clock_end = max(generated_at, _local(issue.clock_snapshot_after)) if issue.clock_snapshot_after is not None else generated_at
        intervals = _timeline(issue, clock_end)
        allocation = calculate_sla_status_durations(
            intervals=tuple(intervals), cycles=issue.cycles, calendars=issue.clock_calendars,
            snapshot_before=issue.clock_snapshot_before, snapshot_after=issue.clock_snapshot_after,
            pause_statuses=issue.clock_pause_statuses,
        )
        durations = allocation.durations
        calendar_name = ", ".join(allocation.calendar_names) or None
        if allocation.warning:
            warnings.append(allocation.warning)
    except ValueError as error:
        warnings.append(str(error))
    breaches: list[SlaViolationBreach] = []
    cycles = []
    for cycle in issue.cycles:
        breached_at = _local(cycle.breached_at) if cycle.breached and cycle.breached_at else None
        status = None
        if cycle.breached:
            if breached_at is None:
                warnings.append("Jira에 정확한 SLA 위반 시각이 없어 위반 당시 상태는 확인 불가입니다.")
            elif breached_at < _local(issue.created_at) or breached_at > generated_at:
                warnings.append("SLA 위반 시각이 티켓 생성~집계 시점 범위를 벗어나 위반 당시 상태는 확인 불가입니다.")
            elif intervals is not None:
                status = next((name for start, end, name in reversed(intervals) if start <= breached_at <= end), None)
            breaches.append(SlaViolationBreach(cycle.metric, breached_at, status))
        cycles.append(replace(cycle, breached_at=breached_at, status=status))
    return SlaViolationTicket(
        key=issue.key,
        summary=issue.summary,
        created_at=_local(issue.created_at),
        elapsed_days=max(0, (generated_at.date() - _local(issue.created_at).date()).days),
        customer=issue.customer,
        partners=issue.partners,
        reporter=issue.reporter,
        assignee=issue.assignee,
        tac_assignee=issue.tac_assignee,
        reporter_account_id=issue.reporter_account_id,
        assignee_account_id=issue.assignee_account_id,
        tac_assignee_account_id=issue.tac_assignee_account_id,
        personal_data_retrieved_at=issue.personal_data_retrieved_at,
        current_status=issue.current_status,
        status_durations=durations,
        breaches=tuple(breaches),
        warnings=tuple(dict.fromkeys(warnings)),
        issue_type=issue.issue_type,
        sla_cycles=tuple(cycles),
        status_durations_basis="resolution_sla",
        status_duration_calendar=calendar_name,
    )


def build_sla_violation_report(
    issues: tuple[SlaViolationIssue, ...],
    period: SlaViolationPeriod,
    selected_date: date,
    generated_at: datetime,
    generated_by: str,
) -> SlaViolationReport:
    generated_at = _local(generated_at)
    if selected_date > generated_at.date():
        raise ValueError("미래 날짜의 보고서는 생성할 수 없습니다.")
    start, end = sla_violation_window(period, selected_date)
    tickets: list[SlaViolationTicket] = []
    seen: set[str] = set()
    for issue in issues:
        created = _local(issue.created_at)
        if not (start <= created < end) or created > generated_at or not any(cycle.breached for cycle in issue.cycles):
            continue
        if issue.key in seen:
            raise ValueError(f"중복 티켓이 수집되었습니다: {issue.key}")
        seen.add(issue.key)
        tickets.append(_ticket(issue, generated_at))
    tickets.sort(key=lambda ticket: (ticket.created_at, ticket.key), reverse=True)
    warning_count = sum(bool(ticket.warnings) for ticket in tickets)
    return SlaViolationReport(
        id=0,
        period=period,
        selected_date=selected_date,
        start_date=start.date(),
        end_date=(end - timedelta(days=1)).date(),
        generated_at=generated_at,
        generated_by=generated_by,
        ticket_count=len(tickets),
        initial_response_count=sum(any(breach.metric == "initial_response" for breach in ticket.breaches) for ticket in tickets),
        resolution_count=sum(any(breach.metric == "resolution" for breach in ticket.breaches) for ticket in tickets),
        tickets=tuple(tickets),
        warnings=(f"{warning_count}개 티켓에 확인이 필요한 데이터가 있습니다. 펼치기에서 상세 사유를 확인하세요.",) if warning_count else (),
    )
