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

@dataclass
class SimpleIssueWidgetData:
    issue_details: list[IssueDetail] = field(default_factory=list)


@dataclass
class TypeCountWidgetData:
    issue_types: list[str] = field(default_factory=list)
    by_type: dict[str, int] = field(default_factory=dict)
    always_included: int = 0
    by_status_type: dict[str, dict[str, int]] = field(default_factory=dict)
    status_breakdown_available: bool = False


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
    tac_assignee: str | None = None
    reporter_account_id: str | None = None
    tac_team_account_id: str | None = None
    tac_assignee_account_id: str | None = None
    personal_data_retrieved_at: str | None = None
    personal_data_field_retrieved_at: dict[str, str] | None = None


@dataclass
class RecentIssueWidgetData:
    issue_details: list[RecentIssueDetail] = field(default_factory=list)

@dataclass
class ResolutionTypeEntry:
    avg_days: float
    avg_hours: float
    count: int


@dataclass
class StageDurationIssue:
    key: str
    type: str
    status: str
    resolved: str
    by_stage_hours: dict[str, float] = field(default_factory=dict)


@dataclass
class ResolutionTypeWidgetData:
    by_type: dict[str, ResolutionTypeEntry] = field(default_factory=dict)
    by_semester: dict[str, dict[str, ResolutionTypeEntry]] = field(default_factory=dict)
    by_status_type: dict[str, dict[str, ResolutionTypeEntry]] = field(default_factory=dict)
    by_semester_status_type: dict[str, dict[str, dict[str, ResolutionTypeEntry]]] = field(default_factory=dict)
    stage_issues: list[StageDurationIssue] | None = None


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
    status: str = "기타"


@dataclass
class CreatedVsResolvedWidgetData:
    created: int = 0
    resolved: int = 0
    created_details: list[CreatedResolvedIssueDetail] = field(default_factory=list)
    resolved_details: list[ResolvedIssueDetail] = field(default_factory=list)

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
    by_status_type: dict[str, dict[str, SlaMonthlyTypeStats]] = field(default_factory=dict)


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
    by_status_type: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class MonthlyCountWidgetData:
    monthly: list[MonthlyCountEntry] = field(default_factory=list)


@dataclass
class RedeploymentIssueDetail:
    key: str
    summary: str
    type: str
    priority: str
    resolved: str
    month: str
    cause: str
    assignee: str
    partners: list[str] = field(default_factory=list)
    assignee_account_id: str | None = None
    personal_data_retrieved_at: str | None = None
    personal_data_field_retrieved_at: dict[str, str] | None = None


@dataclass
class RedeploymentMonthlyEntry:
    month: str
    year: int
    month_num: int
    total: int
    by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class RedeploymentAnalyticsWidgetData:
    resolved_total: int
    redeployment_total: int
    redeployment_rate: float
    analytics_total: int
    classification_complete: bool
    monthly: list[RedeploymentMonthlyEntry] = field(default_factory=list)
    by_cause: dict[str, int] = field(default_factory=dict)
    by_assignee: dict[str, int] = field(default_factory=dict)
    partner_matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    latest_issues: list[RedeploymentIssueDetail] = field(default_factory=list)
    source_jqls: dict[str, str] = field(default_factory=dict)
