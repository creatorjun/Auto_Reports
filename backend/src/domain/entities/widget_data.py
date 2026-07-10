# backend/src/domain/entities/widget_data.py
from dataclasses import dataclass, field


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
class SlaDelayWidgetData:
    by_status: dict[str, int] = field(default_factory=dict)
    distribution: list[SlaDistributionEntry] = field(default_factory=list)
    issue_details: list[SlaViolatedIssueDetail] = field(default_factory=list)


@dataclass
class SimpleIssueWidgetData:
    issue_details: list[IssueDetail] = field(default_factory=list)


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


@dataclass
class MonthlyEntry:
    month: str
    year: int
    month_num: int
    rate: float
    met: int
    total: int


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


@dataclass
class MonthlyCountWidgetData:
    monthly: list[MonthlyCountEntry] = field(default_factory=list)
