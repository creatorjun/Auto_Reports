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
        issue_types_override: list[str] | None = None,
    ) -> "ResolvedQueries":
        return ResolvedQueries(
            now,
            self._c,
            week_start_override,
            issue_types_override,
        )


class ResolvedQueries:
    def __init__(
        self,
        now: datetime,
        c: QueryConfig,
        week_start_override: datetime | None = None,
        issue_types_override: list[str] | None = None,
    ):
        self._now = now
        self._c = c
        self.week_end = now
        self.week_start = week_start_override if week_start_override else now - timedelta(days=6)
        self.date_start = self.week_start.strftime("%Y-%m-%d")
        self.date_end = self.week_end.strftime("%Y-%m-%d")
        raw_issue_types = c.issue_types if issue_types_override is None else issue_types_override
        self._issue_types = tuple(dict.fromkeys(
            issue_type.strip()
            for issue_type in raw_issue_types
            if issue_type.strip()
        ))

    def _project(self) -> str:
        return f"project = {self._c.project_key}"

    def _base(self) -> str:
        return self._project()

    @property
    def issue_types(self) -> tuple[str, ...]:
        return self._issue_types

    @staticmethod
    def _escape_issue_type(issue_type: str) -> str:
        return issue_type.replace('"', '\\"')

    def _formatted_issue_types(self) -> str:
        escaped_types = [self._escape_issue_type(issue_type) for issue_type in self.issue_types]
        return ", ".join(f'"{issue_type}"' for issue_type in escaped_types)

    @staticmethod
    def _with_condition(jql: str, condition: str) -> str:
        order_marker = " ORDER BY "
        if order_marker not in jql:
            return f"{jql} AND {condition}"
        conditions, order = jql.rsplit(order_marker, 1)
        return f"{conditions} AND {condition}{order_marker}{order}"

    def by_issue_type(self, jql: str) -> dict[str, str]:
        queries: dict[str, str] = {}
        for issue_type in self.issue_types:
            escaped = self._escape_issue_type(issue_type)
            queries[issue_type] = self._with_condition(
                jql,
                f'issuetype = "{escaped}"',
            )
        return queries

    def outside_issue_types(self, jql: str) -> str:
        if not self.issue_types:
            return jql
        return self._with_condition(
            jql,
            f"issuetype NOT IN ({self._formatted_issue_types()})",
        )

    def _closed(self) -> str:
        return ", ".join(f'"{s}"' for s in self._c.closed_statuses)

    def _thr(self) -> int:
        return self._c.sla_threshold_days

    def w1_yearly_created(self) -> str:
        year = self._now.year
        return (
            f"{self._base()} "
            f"AND created >= \"{year}-01-01\" "
            f"AND created < \"{year + 1}-01-01\""
        )

    def w2_yearly_resolved(self) -> str:
        year = self._now.year
        return (
            f"{self._base()} "
            f"AND resolved >= \"{year}-01-01\" "
            f"AND resolved < \"{year + 1}-01-01\""
        )

    def w3_created_vs_resolved(self) -> Tuple[str, str]:
        return (
            f"{self._base()} AND created >= \"{self.date_start}\" AND created <= \"{self.date_end}\"",
            f"{self._base()} AND resolved >= \"{self.date_start}\" AND resolved <= \"{self.date_end}\"",
        )

    def w4_issue_review(self) -> str:
        return (
            f"{self._base()} AND status = \"이슈 리뷰 중\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w5_data_request(self) -> str:
        return (
            f"{self._base()} AND status = \"자료 요청 중\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w6_result_pending(self) -> str:
        return (
            f"{self._base()} AND status = \"결과 대기 중\" "
            f"AND status NOT IN ({self._closed()})"
        )

    def w7_recent(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY issuekey DESC"
        )

    def w8_monthly_created(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        return f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""

    def w9_monthly_resolved(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        return f"{self._base()} AND resolved >= \"{start}\" AND resolved < \"{end}\""

    def w10_w11_monthly_candidates(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
        return (
            f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""
            f" ORDER BY created ASC"
        )

    def w12_sla(self) -> str:
        return (
            f"{self._base()} AND status NOT IN ({self._closed()}) "
            f"ORDER BY created ASC"
        )

    def w14_resolution_resolved(self) -> str:
        return (
            f"{self._base()} AND resolved >= \"{self.date_start}\" "
            f"AND resolved <= \"{self.date_end}\" ORDER BY resolved DESC"
        )

    def w15_redeployment_resolved(self) -> str:
        year = self._now.year
        return (
            f"{self._base()} AND status = Closed AND resolution != Unresolved "
            f"AND resolved >= \"{year}-01-01\" AND resolved < \"{year + 1}-01-01\" "
            f"AND type IN (\uac1c\uc120, \uc778\uc2dc\ub358\ud2b8, \"\uc11c\ube44\uc2a4 \uc694\uccad\")"
        )

    def w15_redeployment_issues(self) -> str:
        year = self._now.year
        return (
            f"{self._base()} AND status = Closed "
            f"AND \"\uc7ac\ubc30\ud3ec \uc5ec\ubd80[Dropdown]\" = Y "
            f"AND resolved >= \"{year}-01-01\" AND resolved < \"{year + 1}-01-01\""
        )

    def w15_redeployment_analytics(self) -> str:
        return (
            f"{self.w15_redeployment_issues()} "
            f"AND type IN (\uac1c\uc120, \uc778\uc2dc\ub358\ud2b8, \"\uc11c\ube44\uc2a4 \uc694\uccad\") "
            f"ORDER BY cf[12421] DESC, resolved DESC"
        )
