# backend/src/domain/entities/widget_data.py
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from src.domain.constants import AI_OVERDUE_DETAIL_LIMIT, SUMMARY_TRUNCATE_SHORT_LEN


@runtime_checkable
class AiContextProvider(Protocol):
    def to_ai_context(self) -> dict: ...


@dataclass
class IssueDetail:
    key: str
    summary: str
    type: str
    status: str
    created: str
    elapsed_days: int = 0


@dataclass
class OverdueIssueDetail:
    key: str
    summary: str
    type: str
    created: str
    resp_status: str
    over_h: float


@dataclass
class OverdueWidgetData:
    by_type: dict[str, dict[str, int]] = field(default_factory=dict)
    issue_details: list[OverdueIssueDetail] = field(default_factory=list)

    def to_ai_context(self) -> dict:
        details = [
            f"  - {d.key} [{d.type}] "
            f"{d.summary[:SUMMARY_TRUNCATE_SHORT_LEN]} / "
            f"생성: {d.created} / "
            f"상태: {d.resp_status} / "
            f"초과: +{d.over_h}h"
            for d in self.issue_details[:AI_OVERDUE_DETAIL_LIMIT]
        ]
        return {"overdue_issue_list": "\n".join(details) if details else "  (데이터 없음)"}


@dataclass
class SlaViolatedIssueDetail:
    key: str
    summary: str
    type: str
    status: str
    created: str
    over_h: float


@dataclass
class SlaDistributionEntry:
    status: str
    count: int
    rate: float


@dataclass
class SlaDelayIssueDetail:
    key: str
    summary: str
    type: str
    status: str
    created: str


@dataclass
class SlaDelayWidgetData:
    by_status: dict[str, int] = field(default_factory=dict)
    by_status_details: dict[str, list[SlaDelayIssueDetail]] = field(default_factory=dict)
    distribution: list[SlaDistributionEntry] = field(default_factory=list)
    issue_details: list[SlaViolatedIssueDetail] = field(default_factory=list)

    def to_ai_context(self) -> dict:
        return {"delay_reasons": str(self.by_status)}


@dataclass
class SimpleIssueWidgetData:
    issue_details: list[IssueDetail] = field(default_factory=list)


@dataclass
class TypeCountWidgetData:
    issue_types: list[str] = field(default_factory=list)
    by_type: dict[str, int] = field(default_factory=dict)
    always_included: int = 0


@dataclass
class RecentIssueDetail:
    key: str
    summary: str
    type: str
    status: str
    stage_index: int
    created: str
    elapsed_days: int
    reporter: str = "미지정"
    tac_team: str = "미지정"


@dataclass
class RecentIssueWidgetData:
    issue_details: list[RecentIssueDetail] = field(default_factory=list)

    def to_ai_context(self) -> dict:
        if not self.issue_details:
            return {"avg_resolution_days": 0}
        avg = round(
            sum(d.elapsed_days for d in self.issue_details) / len(self.issue_details),
            1,
        )
        return {"avg_resolution_days": avg}


@dataclass
class ResolutionTypeEntry:
    avg_days: float
    avg_hours: float
    count: int


@dataclass
class ResolutionTypeWidgetData:
    by_type: dict[str, ResolutionTypeEntry] = field(default_factory=dict)


@dataclass
class SlaViolationIssueDetail:
    key: str
    summary: str
    type: str
    status: str
    created: str


@dataclass
class SlaMetVsViolatedEntry:
    stage: str
    field_id: str
    count: int
    rate: float
    issue_details: list[SlaViolationIssueDetail] = field(default_factory=list)


@dataclass
class SlaMetVsViolatedWidgetData:
    initial_response_violations: int = 0
    resolution_violations: int = 0
    both_violations: int = 0
    violation_distribution: list[SlaMetVsViolatedEntry] = field(default_factory=list)

    def to_ai_context(self) -> dict:
        return {"sla_violated": self.initial_response_violations + self.resolution_violations}


@dataclass
class CreatedResolvedIssueDetail:
    key: str
    summary: str
    type: str
    status: str
    created: str


@dataclass
class ResolvedIssueDetail:
    key: str
    summary: str
    type: str
    resolved: str


@dataclass
class CreatedVsResolvedWidgetData:
    created: int = 0
    resolved: int = 0
    created_details: list[CreatedResolvedIssueDetail] = field(default_factory=list)
    resolved_details: list[ResolvedIssueDetail] = field(default_factory=list)

    def to_ai_context(self) -> dict:
        return {"created": self.created, "resolved": self.resolved}


@dataclass
class SlaMonthlyTypeStats:
    met: int = 0
    total: int = 0


@dataclass
class MonthlyEntry:
    month: str
    year: int
    month_num: int
    rate: float
    met: int
    total: int
    by_type: dict[str, SlaMonthlyTypeStats] = field(default_factory=dict)
    always_included: SlaMonthlyTypeStats = field(default_factory=SlaMonthlyTypeStats)


@dataclass
class SlaMonthlyWidgetData:
    monthly: list[MonthlyEntry] = field(default_factory=list)


@dataclass
class BreakdownWidgetData:
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class MonthlyCountEntry:
    month: str
    year: int
    month_num: int
    count: int
    by_type: dict[str, int] = field(default_factory=dict)
    always_included: int = 0


@dataclass
class MonthlyCountWidgetData:
    monthly: list[MonthlyCountEntry] = field(default_factory=list)
