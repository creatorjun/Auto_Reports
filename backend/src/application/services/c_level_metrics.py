# backend/src/application/services/c_level_metrics.py
from collections import Counter
from datetime import datetime, timedelta
import re
from typing import Any

from src.application.services.c_level_periods import CLevelWindow, age_bucket, local_time
from src.application.services.c_level_timeline import CLevelHistory, interval_at, reconstruct_history, status_owner
from src.domain.entities.c_level_report import CLevelIssue, CLevelSlaCycle


TYPE_LABELS = {"all": "전체", "service": "단순문의", "incident": "인시던트", "improvement": "개선"}
_TYPE_ALIASES = {
    "서비스 요청": "service", "서비스(지원) 요청": "service", "서비스 (지원) 요청": "service",
    "인시던트": "incident", "인시던트 보고": "incident", "개선": "improvement", "개선 요청": "improvement",
}
_BUCKETS = (("1-3", "1~3개월", 1, 3), ("3-6", "3~6개월", 3, 6), ("6-12", "6~12개월", 6, 12), ("12+", "12개월 이상", 12, None))
_UNKNOWN = "확인 불가"


def issue_type(issue: CLevelIssue) -> str | None:
    return _TYPE_ALIASES.get(re.sub(r"\s+", " ", issue.issue_type.strip()))


def hours(milliseconds: int | None) -> float | None:
    return round(milliseconds / 3_600_000, 4) if milliseconds is not None else None


def summarize_processing(issues: tuple[CLevelIssue, ...], window: CLevelWindow) -> list[dict[str, Any]]:
    eligible = tuple(issue for issue in issues if local_time(issue.created_at) < window.end)
    histories = {issue.key: reconstruct_history(issue, window.end) for issue in eligible}
    result = []
    for type_key, label in TYPE_LABELS.items():
        selected = [issue for issue in eligible if type_key == "all" or issue_type(issue) == type_key]
        created = [issue for issue in selected if local_time(issue.created_at) >= window.start]
        complete = all(histories[issue.key].complete and not any(window.start <= at < window.end for at in histories[issue.key].unknown_transition_times) for issue in selected)
        state_known = all(histories[issue.key].complete and histories[issue.key].status is not None and histories[issue.key].status.category in {"new", "indeterminate", "done"} for issue in selected)
        done = {
            issue.key: [at for at in histories[issue.key].done_entries if window.start <= at < window.end]
            for issue in selected
        }
        completed = [issue for issue in selected if done[issue.key]]
        cohort_known = all(histories[issue.key].complete and histories[issue.key].status is not None and histories[issue.key].status.category in {"new", "indeterminate", "done"} for issue in created)
        cohort_done = sum(histories[issue.key].status is not None and histories[issue.key].status.category == "done" for issue in created)
        durations = [(max(done[issue.key]) - local_time(issue.created_at)).total_seconds() / 86400 for issue in completed]
        result.append({
            "type": type_key, "label": label, "created": len(created),
            "resolved": len(completed) if complete else None,
            "unresolved": sum(histories[issue.key].status is not None and histories[issue.key].status.category != "done" for issue in selected) if state_known else None,
            "resolution_rate": round(cohort_done / len(created) * 100, 1) if created and cohort_known else None,
            "average_resolution_days": round(sum(durations) / len(durations), 2) if durations and complete else None,
        })
    return result


def issue_details(issue: CLevelIssue, as_of: datetime, collected_at: datetime) -> dict[str, Any]:
    history = reconstruct_history(issue, as_of)
    issue_warnings = list(issue.warnings) + list(history.warnings)
    cycles = []
    for cycle in issue.sla_cycles:
        if cycle.start_at is not None and local_time(cycle.start_at) >= as_of:
            continue
        known_elapsed = (cycle.stop_at is not None and local_time(cycle.stop_at) < as_of) or as_of >= collected_at
        historical_ongoing = cycle.stop_at is None or local_time(cycle.stop_at) >= as_of
        breach_known = cycle.breach_at is not None and local_time(cycle.breach_at) < as_of
        breached = cycle.breached if known_elapsed else (True if cycle.breached is True and breach_known else None)
        excess = _cycle_excess(cycle) if known_elapsed and breached is True else None
        cycles.append({
            "metric": cycle.metric, "cycle_id": cycle.cycle_id,
            "start_at": _iso(cycle.start_at),
            "stop_at": _iso(cycle.stop_at) if cycle.stop_at is not None and local_time(cycle.stop_at) < as_of else None,
            "breach_at": _iso(cycle.breach_at), "goal_hours": hours(cycle.goal_ms),
            "elapsed_hours": hours(cycle.elapsed_ms) if known_elapsed else None,
            "remaining_hours": hours(cycle.remaining_ms) if known_elapsed else None,
            "excess_hours": excess, "breached": breached,
            "paused": cycle.paused if as_of >= collected_at else None,
            "ongoing": historical_ongoing, "historical_elapsed_known": known_elapsed,
        })
        if not known_elapsed:
            issue_warnings.append(f"{issue.key}: {cycle.metric}의 과거 진행 중 SLA 산정시간은 현재 값으로 복원하지 않습니다.")
    owner_hours = {owner: 0.0 for owner in ("TAC", "고객·파트너", "연구소", "기타")}
    unknown_owners: set[str] = set(owner_hours) if not history.complete else set()
    timeline = []
    for index, interval in enumerate(history.intervals):
        if interval.status.category == "done" and interval.end == as_of:
            continue
        duration = (interval.end - interval.start).total_seconds() / 3600
        owner = status_owner(interval.status)
        if interval.status.category not in {"new", "indeterminate", "done"}:
            unknown_owners.add(owner)
        elif interval.status.category != "done":
            owner_hours[owner] += duration
        metrics = sorted({
            cycle.metric for cycle in issue.sla_cycles
            if cycle.breached is True and cycle.breach_at is not None
            and interval.start <= local_time(cycle.breach_at) < interval.end
        })
        timeline.append({
            "id": f"{issue.key}:{index}", "status": interval.status.name,
            "status_id": interval.status.id, "status_category": interval.status.category,
            "owner": owner, "start_at": interval.start.isoformat(), "end_at": interval.end.isoformat(),
            "duration_hours": round(duration, 4), "is_current": index == len(history.intervals) - 1,
            "breached_metrics": metrics,
        })
    first_responses = [local_time(cycle.stop_at) for cycle in issue.sla_cycles if cycle.metric == "initial_response" and cycle.stop_at is not None and local_time(cycle.stop_at) < as_of]
    first_response_source = "sla_cycle" if first_responses else None
    first_response = min(first_responses) if first_responses else None
    if first_response is None and issue.first_response_at is not None and local_time(issue.first_response_at) < as_of:
        first_response = local_time(issue.first_response_at)
        first_response_source = "jira_first_response_field"
        issue_warnings.append(f"{issue.key}: 최초응답 SLA 종료시각이 없어 Jira 최초응답 보조 필드를 표시합니다.")
    reopen_times = [
        local_time(change.changed_at) for change in issue.status_changes
        if change.from_status.category == "done" and change.to_status.category != "done"
        and local_time(change.changed_at) < as_of
    ]
    if reopen_times and not any(cycle.start_at is not None and max(reopen_times) <= local_time(cycle.start_at) < as_of for cycle in issue.sla_cycles if cycle.metric == "resolution"):
        issue_warnings.append(f"{issue.key}: 재오픈 이후 해결 SLA cycle이 없어 이전 완료 cycle만 표시합니다.")
    reference_date = (as_of - timedelta(microseconds=1)).date()
    mapped_type = issue_type(issue)
    return {
        "key": issue.key, "summary": issue.summary, "issue_type": issue.issue_type,
        "type": mapped_type, "type_label": TYPE_LABELS.get(mapped_type, issue.issue_type),
        "customer_name": issue.customer_name or _UNKNOWN, "partner_names": list(issue.partner_names),
        "reporter": issue.reporter, "assignee": issue.assignee, "tac_assignee": issue.tac_assignee,
        "created_at": local_time(issue.created_at).isoformat(), "updated_at": _iso(issue.updated_at) if issue.updated_at is not None and local_time(issue.updated_at) < as_of else None,
        "status": history.status.name if history.status else _UNKNOWN,
        "status_category": history.status.category or None if history.status else None,
        "history_complete": history.complete, "reopen_count": history.reopen_count,
        "age_days": max(0, (reference_date - local_time(issue.created_at).date()).days),
        "age_bucket": age_bucket(issue.created_at, as_of),
        "is_unresolved": history.status.category != "done" if history.status and history.status.category in {"new", "indeterminate", "done"} else None,
        "first_response_at": _iso(first_response), "first_response_source": first_response_source, "timeline": timeline,
        "owner_hours": {owner: None if owner in unknown_owners else round(duration, 4) for owner, duration in owner_hours.items()},
        "sla_cycles": cycles, "warnings": list(dict.fromkeys(issue_warnings)),
        "jira_delay_reason": issue.jira_delay_reason, "jira_delay_responsibility": issue.jira_delay_responsibility,
    }


def summarize_long_term(details: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = [{"id": key, "label": label, "min_months": minimum, "max_months": maximum, "count": 0, "customer_count": 0, "by_type": {kind: 0 for kind in TYPE_LABELS if kind != "all"}} for key, label, minimum, maximum in _BUCKETS]
    bucket_by_id = {bucket["id"]: bucket for bucket in buckets}
    bucket_customers: dict[str, set[str]] = {bucket["id"]: set() for bucket in buckets}
    customers: dict[str, dict[str, Any]] = {}
    for detail in details:
        if detail["is_unresolved"] is not True or detail["age_bucket"] is None:
            continue
        name = re.sub(r"\s+", " ", detail["customer_name"].strip()) or _UNKNOWN
        customer_key = name.casefold()
        bucket_id, type_key = detail["age_bucket"], detail["type"]
        bucket = bucket_by_id[bucket_id]
        bucket["count"] += 1
        bucket["by_type"][type_key] += 1
        if name != _UNKNOWN:
            bucket_customers[bucket_id].add(customer_key)
        customer = customers.setdefault(customer_key, {
            "customer_key": customer_key, "customer_name": name, "partners": set(), "tac_assignees": set(),
            "total": 0, "by_type": {kind: 0 for kind in TYPE_LABELS if kind != "all"},
            "buckets": {key: 0 for key, _, _, _ in _BUCKETS}, "oldest_days": 0,
            "dominant_status": "", "issue_keys": [], "issues": [],
        })
        customer["total"] += 1
        customer["by_type"][type_key] += 1
        customer["buckets"][bucket_id] += 1
        customer["oldest_days"] = max(customer["oldest_days"], detail["age_days"])
        customer["partners"].update(detail["partner_names"])
        if detail["tac_assignee"]:
            customer["tac_assignees"].add(detail["tac_assignee"])
        customer["issue_keys"].append(detail["key"])
        customer["issues"].append({
            "key": detail["key"], "type": type_key, "bucket": bucket_id, "age_days": detail["age_days"],
            "status": detail["status"], "tac_assignee": detail["tac_assignee"], "partner_names": detail["partner_names"],
        })
    for bucket in buckets:
        bucket["customer_count"] = len(bucket_customers[bucket["id"]])
        bucket["known_count"] = bucket["count"]
        uncertain = [detail for detail in details if detail["is_unresolved"] is None and detail["age_bucket"] == bucket["id"]]
        bucket["unknown_status_count"] = len(uncertain)
        if uncertain:
            bucket["count"] = None
            bucket["customer_count"] = None
            for detail in uncertain:
                bucket["by_type"][detail["type"]] = None
    for customer in customers.values():
        customer["partners"] = sorted(customer["partners"])
        customer["tac_assignees"] = sorted(customer["tac_assignees"])
        customer["dominant_status"] = Counter(issue["status"] for issue in customer["issues"]).most_common(1)[0][0]
        customer["issues"].sort(key=lambda issue: (-issue["age_days"], issue["key"]))
    return {
        "buckets": buckets,
        "customers": sorted(customers.values(), key=lambda customer: (-customer["total"], -customer["oldest_days"], customer["customer_key"])),
        "unknown_status_issue_count": sum(detail["is_unresolved"] is None for detail in details),
        "unassigned_customer_issue_count": sum(customer["total"] for customer in customers.values() if customer["customer_name"] == _UNKNOWN),
    }


def long_term_counts(issues: tuple[CLevelIssue, ...], as_of: datetime) -> tuple[int | None, int | None]:
    total: int | None = 0
    over_12_months: int | None = 0
    for issue in issues:
        if local_time(issue.created_at) >= as_of:
            continue
        bucket = age_bucket(issue.created_at, as_of)
        if bucket is None:
            continue
        history = reconstruct_history(issue, as_of)
        if not history.complete or history.status is None or history.status.category not in {"new", "indeterminate", "done"}:
            total = None
            if bucket == "12+":
                over_12_months = None
        elif history.status.category != "done":
            if total is not None:
                total += 1
            if bucket == "12+" and over_12_months is not None:
                over_12_months += 1
    return total, over_12_months


def summarize_sla(issues: tuple[CLevelIssue, ...], details: list[dict[str, Any]], window: CLevelWindow, collected_at: datetime) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    by_type = {
        type_key: {"type": type_key, "label": label, **{metric: {"violations": 0, "evaluated": 0, "met": 0, "compliance_rate": None} for metric in ("initial_response", "resolution")}}
        for type_key, label in TYPE_LABELS.items() if type_key != "all"
    }
    detail_by_key = {detail["key"]: detail for detail in details}
    violations, warnings = [], []
    reasons: Counter[tuple[str, str]] = Counter()
    type_issue_counts = Counter(issue_type(issue) for issue in issues)
    metric_known_cycles: Counter[tuple[str, str]] = Counter()
    metric_missing_issues: Counter[tuple[str, str]] = Counter()
    known_cycles = unknown_cycles = without_sla = 0
    for issue in issues:
        detail = detail_by_key[issue.key]
        mapped_type = issue_type(issue)
        history = reconstruct_history(issue, window.end)
        if not issue.sla_cycles:
            without_sla += 1
        for metric in ("initial_response", "resolution"):
            if not any(cycle.metric == metric and cycle.breached is not None and (cycle.start_at is None or local_time(cycle.start_at) < window.end) for cycle in issue.sla_cycles):
                metric_missing_issues[(mapped_type, metric)] += 1
        seen: set[tuple[str, str, str | None, str | None]] = set()
        for cycle in issue.sla_cycles:
            identity = (cycle.metric, cycle.cycle_id, _iso(cycle.start_at), _iso(cycle.stop_at))
            if identity in seen or cycle.metric not in {"initial_response", "resolution"}:
                continue
            seen.add(identity)
            if cycle.start_at is not None and local_time(cycle.start_at) >= window.end:
                continue
            stats = by_type[mapped_type][cycle.metric]
            if cycle.breached is None:
                unknown_cycles += 1
                continue
            known_cycles += 1
            metric_known_cycles[(mapped_type, cycle.metric)] += 1
            stop_at = local_time(cycle.stop_at) if cycle.stop_at else None
            breach_at = local_time(cycle.breach_at) if cycle.breach_at else None
            completed_in_period = stop_at is not None and window.start <= stop_at < window.end
            breached_in_period = cycle.breached is True and breach_at is not None and window.start <= breach_at < window.end
            ongoing_at_cutoff = stop_at is None or stop_at >= window.end
            if completed_in_period or (ongoing_at_cutoff and breached_in_period):
                stats["evaluated"] += 1
                stats["met"] += int(not cycle.breached)
            if cycle.breached is True and breach_at is None:
                warnings.append(f"{issue.key}: {cycle.metric} 위반 발생시각이 없어 기간별 신규 위반에서 제외했습니다.")
            if not breached_in_period:
                continue
            stats["violations"] += 1
            interval = interval_at(history, breach_at)
            reason = interval.status.name if interval else _UNKNOWN
            owner = status_owner(interval.status) if interval else "기타"
            reasons[(reason, owner)] += 1
            elapsed_known = (stop_at is not None and stop_at < window.end) or window.end >= collected_at
            violations.append({
                "id": f"{issue.key}:{cycle.metric}:{cycle.cycle_id}", "issue_key": issue.key,
                "summary": issue.summary, "type": mapped_type, "type_label": TYPE_LABELS[mapped_type],
                "customer_name": detail["customer_name"], "metric": cycle.metric, "cycle_id": cycle.cycle_id,
                "goal_hours": hours(cycle.goal_ms), "elapsed_hours": hours(cycle.elapsed_ms) if elapsed_known else None,
                "excess_hours": _cycle_excess(cycle) if elapsed_known else None,
                "breach_at": _iso(breach_at), "status": detail["status"],
                "status_at_breach": reason, "owner_at_breach": owner,
                "paused": cycle.paused if window.end >= collected_at else None, "is_ongoing": ongoing_at_cutoff,
            })
    for type_stats in by_type.values():
        for metric in ("initial_response", "resolution"):
            stats = type_stats[metric]
            type_key = type_stats["type"]
            missing = metric_missing_issues[(type_key, metric)]
            stats["coverage"] = {"issue_count": type_issue_counts[type_key], "known_cycles": metric_known_cycles[(type_key, metric)], "issues_without_known_cycle": missing}
            if type_issue_counts[type_key] and not metric_known_cycles[(type_key, metric)]:
                stats.update(violations=None, evaluated=None, met=None)
            elif missing:
                warnings.append(f"{TYPE_LABELS[type_key]} {metric}: SLA를 확인할 수 없는 이슈 {missing}건을 제외한 확인 가능 자료만 집계했습니다.")
            if stats["evaluated"]:
                stats["compliance_rate"] = round(stats["met"] / stats["evaluated"] * 100, 1)
    violations.sort(key=lambda item: (item["excess_hours"] is None, -(item["excess_hours"] or 0), item["issue_key"], item["metric"]))
    total = len(violations)
    sla = {
        "by_type": list(by_type.values()), "violation_ticket_count": len({item["issue_key"] for item in violations}) if known_cycles or not issues else None,
        "violation_event_count": total if known_cycles or not issues else None,
        "delay_reasons": [{"status": status, "owner": owner, "count": count, "percentage": round(count / total * 100, 1)} for (status, owner), count in reasons.most_common()],
        "coverage": {"known_cycles": known_cycles, "unknown_cycles": unknown_cycles, "issues_without_sla": without_sla},
    }
    return sla, violations, warnings


def _cycle_excess(cycle: CLevelSlaCycle) -> float | None:
    if cycle.remaining_ms is not None:
        return hours(max(0, -cycle.remaining_ms))
    if cycle.elapsed_ms is not None and cycle.goal_ms is not None:
        return hours(max(0, cycle.elapsed_ms - cycle.goal_ms))
    return None


def _iso(value: datetime | None) -> str | None:
    return local_time(value).isoformat() if value is not None else None
