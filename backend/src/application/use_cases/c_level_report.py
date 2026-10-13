# backend/src/application/use_cases/c_level_report.py
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from src.application.ports.c_level_port import CLevelSourcePort
from src.application.services.c_level_metrics import issue_details, issue_type, long_term_counts, summarize_long_term, summarize_processing, summarize_sla
from src.application.services.c_level_periods import local_time, report_windows
from src.domain.constants import KST


POLICY_VERSION = "c-level-1.0"
POLICY_LABELS = (
    "대상: 단순문의(서비스 요청), 인시던트, 개선. CVE·H/W 장애·라이선스 등 나머지 유형은 제외합니다.",
    "요청 유형의 대상 선정과 분류는 Jira의 현재 유형을 사용합니다. 조회 기간 이후 유형이 변경된 이슈를 당시 유형으로 재분류하지 않습니다.",
    "접수는 기간 내 생성, 해결은 기간 내 비완료→완료(Done) 전환 이슈의 중복 제거 건수, 미해결은 기준시점 비완료 잔량입니다.",
    "해결률은 해당 기간 접수 건 중 기준시점 완료 비율입니다. 평균 해결일은 기간 내 마지막 Done 진입까지 생성일부터의 달력 시간입니다.",
    "주간은 종료일을 포함한 최근 7일입니다. 현재 진행 중 기간은 현재시각까지, 이전 기간은 같은 경과 시점까지 비교합니다.",
    "월간은 선택 월 전체 또는 현재 월 누적입니다. 현재 월 비교는 이전 월의 같은 날짜·시각까지이며 짧은 달은 말일로 제한합니다.",
    "장기 구간은 생성일과 기준일의 달력상 1·3·6·12개월 경계로 구분하며, 고객사 확인 불가 건은 이슈 수에 포함하고 고객사 수에서는 제외합니다.",
    "SLA 신규 위반은 위반 cycle의 breachTime이 조회 기간에 속하는 사건 수입니다. 총 티켓 수는 이슈 키로 중복 제거합니다.",
    "SLA 준수율 분모는 기간 내 완료 cycle과 기준시점 진행 중이며 기간 내 이미 위반한 cycle입니다. 미적용·판정 불가·미완료 정상 건은 준수로 간주하지 않습니다.",
    "SLA 목표·실소요·초과는 Jira가 산정한 업무시간 값이며 과거 진행 cycle의 소요시간을 현재 값으로 대체하지 않습니다. 기준 준수율 목표는 80%입니다.",
    "상태 체류시간은 달력 시간이며 책임 구간 합계는 완료 상태를 제외합니다. 위반 시점 상태는 실제 지연 원인 또는 책임 확정이 아닙니다.",
    "고객사·파트너·담당자는 조회 기준시점으로 복원 가능한 이력을 적용하며, 복원 불가 항목은 확인 불가로 표시합니다.",
    "보고 기준과 원본 이력은 저장 시점에 동결됩니다. 조회 기간 후 변경된 Jira SLA 정책의 과거 진행 상태까지 재현할 수는 없습니다.",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return local_time(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


class CLevelReportUseCase:
    def __init__(self, source: CLevelSourcePort) -> None:
        self._source = source

    async def execute(
        self,
        period: str = "week",
        end_date: date | None = None,
        refresh: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        collected_at = local_time(now or datetime.now(KST))
        window, previous_window, trend_windows = report_windows(period, end_date, collected_at)
        raw_issues = await self._source.fetch_issues(trend_windows[0].start, window.end, refresh)
        issues_by_key = {issue.key: issue for issue in raw_issues if issue.key and issue_type(issue) is not None and local_time(issue.created_at) < window.end}
        issues = tuple(sorted(issues_by_key.values(), key=lambda issue: issue.key))
        summary = summarize_processing(issues, window)
        previous = {item["type"]: item for item in summarize_processing(issues, previous_window)}
        for card in summary:
            previous_card = previous[card["type"]]
            card["previous"] = {key: value for key, value in previous_card.items() if key not in {"type", "label"}}
            card["delta"] = {metric: card[metric] - previous_card[metric] if card[metric] is not None and previous_card[metric] is not None else None for metric in ("created", "resolved", "unresolved")}
        trend = []
        for trend_window in trend_windows:
            metrics = summarize_processing(issues, trend_window)
            total = metrics[0]
            trend.append({
                "label": trend_window.start.strftime("%Y-%m" if period == "month" else "%m/%d"),
                "start_date": trend_window.start_date, "end_date": trend_window.end_date,
                "created": total["created"], "resolved": total["resolved"], "unresolved": total["unresolved"],
                "by_type": [{key: card[key] for key in ("type", "label", "created", "resolved", "unresolved")} for card in metrics],
            })
        details = [issue_details(issue, window.end, collected_at) for issue in issues]
        long_term = summarize_long_term(details)
        current_total, current_over_12 = long_term_counts(issues, window.end)
        previous_total, previous_over_12 = long_term_counts(issues, previous_window.end)
        long_term.update(
            previous_total=previous_total,
            delta_total=current_total - previous_total if current_total is not None and previous_total is not None else None,
            previous_over_12_months=previous_over_12,
            delta_over_12_months=current_over_12 - previous_over_12 if current_over_12 is not None and previous_over_12 is not None else None,
        )
        sla, violations, sla_warnings = summarize_sla(issues, details, window, collected_at)
        warnings = [warning for detail in details for warning in detail["warnings"]]
        warnings.extend(sla_warnings)
        if sla["coverage"]["issues_without_sla"]:
            warnings.append(f"SLA cycle이 없는 이슈 {sla['coverage']['issues_without_sla']}건은 SLA 준수율 분모에서 제외했습니다.")
        if sla["coverage"]["unknown_cycles"]:
            warnings.append(f"위반 여부를 확인할 수 없는 SLA cycle {sla['coverage']['unknown_cycles']}개는 준수율 분모에서 제외했습니다.")
        return {
            "period": period, "start_date": window.start_date, "end_date": window.end_date,
            "as_of": window.end.isoformat(), "previous_start_date": previous_window.start_date,
            "previous_end_date": previous_window.end_date, "generated_at": collected_at.isoformat(),
            "policy_version": POLICY_VERSION, "policy_labels": list(POLICY_LABELS),
            "warnings": list(dict.fromkeys(warnings)), "summary": summary, "trend": trend,
            "long_term": long_term, "sla": sla, "violations": violations,
            "issues": details, "source_issues": [_json_value(asdict(issue)) for issue in issues],
        }
