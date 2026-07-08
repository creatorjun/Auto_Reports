# backend/src/application/services/query_builder.py
from datetime import datetime, timedelta
from typing import Tuple

from src.application.services.query_config import QueryConfig


class WidgetQueryBuilder:
    def __init__(self, config: QueryConfig):
        self._c = config

    def build(self, now: datetime) -> "ResolvedQueries":
        return ResolvedQueries(now, self._c)


class ResolvedQueries:
    def __init__(self, now: datetime, c: QueryConfig):
        self._now = now
        self._c = c
        self.week_end = now
        self.week_start = now - timedelta(days=6)
        self.date_start = self.week_start.strftime("%Y-%m-%d")
        self.date_end = self.week_end.strftime("%Y-%m-%d")

    def _base(self) -> str:
        types = ", ".join(f'"{t}"' if " " in t else t for t in self._c.issue_types)
        return f"project = {self._c.project_key} AND issuetype IN ({types})"

    def _closed(self) -> str:
        return ", ".join(f'"{s}"' for s in self._c.closed_statuses)

    def _thr(self) -> int:
        return self._c.sla_threshold_days

    # w1: 연도 누적 생성
    def w1_yearly_created(self) -> str:
        return f"{self._base()} AND created >= \"{self._c.year_start}-01-01\""

    # w2: 연도 누적 해결
    def w2_yearly_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"{self._c.year_start}-01-01\""

    # w3: 주간 생성 vs 해결
    def w3_created_vs_resolved(self) -> Tuple[str, str]:
        return (
            f"{self._base()} AND created >= \"-7d\"",
            f"{self._base()} AND resolved >= \"-7d\"",
        )

    # w4: 이슈 리뷰 중
    def w4_issue_review(self) -> str:
        return (
            f"{self._base()} AND status = \"이슈 리뷰 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    # w5: 자료 요청 중
    def w5_data_request(self) -> str:
        return (
            f"{self._base()} AND status = \"자료 요청 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    # w6: 결과 대기 중
    def w6_result_pending(self) -> str:
        return (
            f"{self._base()} AND status = \"결과 대기 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    # w7 / w8: 월별 SLA (MonthlyCollector 사용)
    def w7_w8_monthly_candidates(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        return (
            f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""
            f" ORDER BY created ASC"
        )

    # w9: SLA 준수 vs 위반
    def w9_sla(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created ASC"
        )

    # w10: SLA 지연 사유
    def w10_sla_violated(self) -> str:
        return (
            f"{self._base()} AND created <= \"-{self._thr()}d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    # w11: 유형별 평균 처리일
    def w11_resolution_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"-7d\" ORDER BY resolved DESC"

    # w12: 최근 활성 이슈
    def w12_recent(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created DESC"
        )

    # w13: SLA 초과 지연 이슈 상세
    def w13_overdue(self) -> str:
        return (
            f"{self._base()} AND created <= \"-{self._thr()}d\" "
            f"AND updated >= \"-7d\" AND status NOT IN ({self._closed()})"
        )

    def w13_by_type_status(self) -> dict[str, dict[str, str]]:
        result = {}
        for itype in self._c.issue_types:
            iq = f'"{itype}"' if " " in itype else itype
            result[itype] = {}
            for st in self._c.active_statuses:
                result[itype][st] = (
                    f"project = {self._c.project_key} AND issuetype = {iq} "
                    f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" AND status = \"{st}\""
                )
        return result
