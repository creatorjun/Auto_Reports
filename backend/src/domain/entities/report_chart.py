# backend/src/domain/entities/report_chart.py
from dataclasses import dataclass, field
from enum import Enum


class ReportChartKind(str, Enum):
    SLA_INITIAL = "sla_initial"
    SLA_RESOLUTION = "sla_resolution"
    RESOLUTION_TYPE = "resolution_type"
    REDEPLOYMENT = "redeployment"


@dataclass(frozen=True)
class ReportChartSelection:
    chart: ReportChartKind
    month: int | None = None
    issue_type: str | None = None
    semester: str | None = None
    partner: str | None = None
    cause: str | None = None
    assignee: str | None = None
    selected_types: tuple[str, ...] | None = None
    sla_status: str = "all"
    selected_statuses: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.chart, ReportChartKind):
            raise ValueError("지원하지 않는 그래프입니다.")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError("월은 1부터 12까지 지정해야 합니다.")
        if self.semester not in (None, "h1", "h2"):
            raise ValueError("반기 값이 올바르지 않습니다.")
        for value in (self.issue_type, self.partner, self.cause, self.assignee):
            if value is not None and (not value.strip() or len(value) > 200 or any(ord(c) < 32 for c in value)):
                raise ValueError("상세 조회 조건이 올바르지 않습니다.")
        if self.selected_types is not None:
            if len(self.selected_types) > 50 or any(not value.strip() or len(value) > 200 for value in self.selected_types):
                raise ValueError("요청 유형 필터가 올바르지 않습니다.")
        if self.selected_statuses is not None:
            if len(self.selected_statuses) > 50 or any(
                not value.strip() or len(value) > 200 or any(ord(character) < 32 for character in value)
                for value in self.selected_statuses
            ):
                raise ValueError("진행 상태 필터가 올바르지 않습니다.")
        sla = self.chart in (ReportChartKind.SLA_INITIAL, ReportChartKind.SLA_RESOLUTION)
        if self.sla_status not in ("all", "met", "violated") or (not sla and self.sla_status != "all"):
            raise ValueError("SLA 상태 필터가 올바르지 않습니다.")
        if sla and self.month is None:
            raise ValueError("월별 SLA 상세 조회에는 월이 필요합니다.")
        if self.chart == ReportChartKind.RESOLUTION_TYPE and self.month is not None:
            raise ValueError("유형별 처리일에는 월 필터를 사용할 수 없습니다.")
        dimensions = (self.partner, self.cause, self.assignee)
        if self.chart != ReportChartKind.REDEPLOYMENT and any(value is not None for value in dimensions):
            raise ValueError("재배포 전용 필터입니다.")
        if self.chart == ReportChartKind.REDEPLOYMENT:
            if sum(value is not None for value in (self.month, *dimensions)) > 1:
                raise ValueError("재배포 상세 항목은 한 번에 하나만 선택할 수 있습니다.")
            if self.semester is not None:
                raise ValueError("재배포 통계는 연간 전체 기준입니다.")
            if self.selected_statuses is not None:
                raise ValueError("재배포 통계는 전체 진행 상태 기준입니다.")
        if self.month is not None and self.semester is not None:
            if (self.month <= 6) != (self.semester == "h1"):
                raise ValueError("선택한 월이 반기 범위에 포함되지 않습니다.")


@dataclass(frozen=True)
class ReportChartIssue:
    key: str
    summary: str
    type: str
    status: str | None = None
    created: str | None = None
    resolved: str | None = None
    elapsed_hours: float | None = None
    sla_met: bool | None = None
    month: str | None = None
    cause: str | None = None
    assignee: str | None = None
    partners: list[str] = field(default_factory=list)
    priority: str | None = None


@dataclass(frozen=True)
class ReportChartIssueResult:
    issues: list[ReportChartIssue]
    snapshot_count: int | None
    current_count: int
    source_total: int
    source_total_exact: bool
    collection_limit: int | None
    truncated: bool
    queried_at: str
    snapshot_at: str
    source: str = "current_jira"
