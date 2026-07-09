# backend/src/application/services/query_builder.py
from datetime import datetime, timedelta
from typing import Tuple

from src.application.services.query_config import QueryConfig


class WidgetQueryBuilder:
    def __init__(self, config: QueryConfig):
        self._c = config

    def build(
        self,
        now: datetime,
        week_start_override: datetime | None = None,
    ) -> "ResolvedQueries":
        return ResolvedQueries(now, self._c, week_start_override)


class ResolvedQueries:
    def __init__(
        self,
        now: datetime,
        c: QueryConfig,
        week_start_override: datetime | None = None,
    ):
        self._now = now
        self._c = c
        self.week_end = now
        self.week_start = week_start_override if week_start_override else now - timedelta(days=6)
        self.date_start = self.week_start.strftime("%Y-%m-%d")
        self.date_end = self.week_end.strftime("%Y-%m-%d")

    def _base(self) -> str:
        types = ", ".join(f'"{t}"' if " " in t else t for t in self._c.issue_types)
        return f"project = {self._c.project_key} AND issuetype IN ({types})"

    def _closed(self) -> str:
        return ", ".join(f'"{s}"' for s in self._c.closed_statuses)

    def _thr(self) -> int:
        return self._c.sla_threshold_days

    def w1_yearly_created(self) -> str:
        return f"{self._base()} AND created >= \"{self._c.year_start}-01-01\""

    def w2_yearly_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"{self._c.year_start}-01-01\""

    def w3_created_vs_resolved(self) -> Tuple[str, str]:
        return (
            f"{self._base()} AND created >= \"-7d\"",
            f"{self._base()} AND resolved >= \"-7d\"",
        )

    def w4_issue_review(self) -> str:
        return (
            f"{self._base()} AND status = \"이슈 리뷰 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w5_data_request(self) -> str:
        return (
            f"{self._base()} AND status = \"자료 요청 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w6_result_pending(self) -> str:
        return (
            f"{self._base()} AND status = \"결과 대기 중\" "
            f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w7_w8_monthly_candidates(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        return (
            f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""
            f" ORDER BY created ASC"
        )

    def w9_sla(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created ASC"
        )

    def w10_sla_violated(self) -> str:
        return (
            f"{self._base()} AND created <= \"-{self._thr()}d\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w11_resolution_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"-7d\" ORDER BY resolved DESC"

    def w12_recent(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY issuekey DESC"
        )
