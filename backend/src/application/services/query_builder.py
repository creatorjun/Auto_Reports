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

    # w1: SLA 지연 이슈 (스냅쇷 + 상세)
    def w1_overdue(self) -> str:
        return (f"{self._base()} AND created <= \"-{self._thr()}d\" "
                f"AND updated >= \"-7d\" AND status NOT IN ({self._closed()})")

    def w1_by_type_status(self) -> dict[str, dict[str, str]]:
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

    # w2: 이슈 리뷰 중
    def w2_issue_review(self) -> str:
        return (f"{self._base()} AND status = \"이슈 리뷰 중\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    # w3: 자료 요청 중
    def w3_data_request(self) -> str:
        return (f"{self._base()} AND status = \"자료 요청 중\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    # w4: SLA 지연 사유 (by_status)
    def w4_sla_violated(self) -> str:
        return (
            f"{self._base()} AND created <= \"-{self._thr()}d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    # w5: 연도 누적 생성
    def w5_yearly_created(self) -> str:
        return f"{self._base()} AND created >= \"{self._c.year_start}-01-01\""

    # w6: 연도 누적 해결
    def w6_yearly_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"{self._c.year_start}-01-01\""

    # w7: 유형별 평균 처리일
    def w7_resolution_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"-7d\" ORDER BY resolved DESC"

    # w8: 최근 이슈 (활성 이슈 목록)
    def w8_recent(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created DESC"
        )

    # w9: SLA 준수 vs 위반
    def w9_sla(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created ASC"
        )

    # w10: 결과 대기 중
    def w10_result_pending(self) -> str:
        return (f"{self._base()} AND status = \"결과 대기 중\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    # w11: 주간 생성 vs 해결
    def w11_created_vs_resolved(self) -> Tuple[str, str]:
        return (f"{self._base()} AND created >= \"-7d\"",
                f"{self._base()} AND resolved >= \"-7d\"")

    # w12 / w13: 월별 SLA (MonthlyCollector 사용)
    def w12_w13_monthly_candidates(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        return (
            f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""
            f" ORDER BY created ASC"
        )
