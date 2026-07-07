from datetime import datetime, timedelta
from typing import Tuple

from src.config.settings import Settings


class WidgetQueryBuilder:
    def __init__(self, settings: Settings):
        self._s = settings

    def build(self, now: datetime) -> "ResolvedQueries":
        return ResolvedQueries(now, self._s)


class ResolvedQueries:
    def __init__(self, now: datetime, s: Settings):
        self._now = now
        self._s = s
        self.week_end = now
        self.week_start = now - timedelta(days=6)
        self.date_start = self.week_start.strftime("%Y-%m-%d")
        self.date_end = self.week_end.strftime("%Y-%m-%d")

    def _base(self) -> str:
        types = ", ".join(f'"{t}"' if " " in t else t for t in self._s.issue_types)
        return f"project = {self._s.project_key} AND issuetype IN ({types})"

    def _closed(self) -> str:
        return ", ".join(f'"{s}"' for s in self._s.closed_statuses)

    def _thr(self) -> int:
        return self._s.sla_threshold_days

    def w1_overdue(self) -> str:
        return (f"{self._base()} AND created <= \"-{self._thr()}d\" "
                f"AND updated >= \"-7d\" AND status NOT IN ({self._closed()})")

    def w1_by_type_status(self) -> dict[str, dict[str, str]]:
        result = {}
        for itype in self._s.issue_types:
            iq = f'"{itype}"' if " " in itype else itype
            result[itype] = {}
            for st in self._s.active_statuses:
                result[itype][st] = (
                    f"project = {self._s.project_key} AND issuetype = {iq} "
                    f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" AND status = \"{st}\""
                )
        return result

    def w2_issue_review(self) -> str:
        """\uc774\uc288 \ub9ac\ubdf0 \uc911 \uc0c1\ud0dc\uc5d0\uc11c SLA \ucd08\uacfc"""
        return (f"{self._base()} AND status = \"\uc774\uc288 \ub9ac\ubdf0 \uc911\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    def w3_data_request(self) -> str:
        """\uc790\ub8cc \uc694\uccad \uc911 \uc0c1\ud0dc\uc5d0\uc11c SLA \ucd08\uacfc"""
        return (f"{self._base()} AND status = \"\uc790\ub8cc \uc694\uccad \uc911\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    def w13_result_pending(self) -> str:
        """\uacb0\uacfc \ub300\uae30 \uc911 \uc0c1\ud0dc\uc5d0\uc11c SLA \ucd08\uacfc"""
        return (f"{self._base()} AND status = \"\uacb0\uacfc \ub300\uae30 \uc911\" "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    def w4_lab_unassigned(self) -> str:
        return (f"{self._base()} AND status = \"\uc5f0\uad6c\uc18c \ub300\uae30 \uc911\" AND assignee IS EMPTY "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\"")

    def w5_by_type(self) -> dict[str, str]:
        result = {}
        for itype in self._s.issue_types:
            iq = f'"{itype}"' if " " in itype else itype
            result[itype] = (f"project = {self._s.project_key} AND issuetype = {iq} "
                             f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                             f"AND status NOT IN ({self._closed()})")
        return result

    def w6_by_status(self) -> dict[str, str]:
        result = {}
        for st in self._s.active_statuses:
            result[st] = (f"{self._base()} AND created <= \"-{self._thr()}d\" "
                          f"AND updated >= \"-7d\" AND status = \"{st}\"")
        return result

    def w7_reason_pie(self) -> dict[str, str]:
        base = f"{self._base()} AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\""
        return {
            "TAC \ucc98\ub9ac \uc9c0\uc5f0": f"{base} AND status IN (\"\ud560 \uc77c\",\"\uc774\uc288 \ub9ac\ubdf0 \uc911\")",
            "\uc5f0\uad6c\uc18c \ub300\uae30": f"{base} AND status IN (\"\uc5f0\uad6c\uc18c \ub300\uae30 \uc911\",\"\uc5f0\uad6c\uc18c \uac80\ud1a0 \uc911\")",
            "\uac1c\ubc1c \uc9c4\ud589 \uc911": f"{base} AND status IN (\"\uad6c\ud604 \uc911\",\"\ubc30\ud3ec \ud30c\uc77c \uac80\ud1a0 \uc911\")",
            "\uace0\uac1d \uc751\ub2f5 \ub300\uae30": f"{base} AND status IN (\"\uc790\ub8cc \uc694\uccad \uc911\",\"\uacb0\uacfc \ub300\uae30 \uc911\")",
            "\ubcf4\ub958": f"{base} AND status = \"\ubcf4\ub958 \uc911\"",
            "\uc601\uc5c5 \uac80\ud1a0": f"{base} AND status = \"\uc601\uc5c5\ubcf8\ubd80 \uac80\ud1a0\uc911\"",
        }

    def w8_yearly_created(self) -> str:
        return f"{self._base()} AND created >= \"2026-01-01\""

    def w9_yearly_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"2026-01-01\""

    def w10_11_resolved(self) -> str:
        return f"{self._base()} AND resolved >= \"-7d\" ORDER BY resolved DESC"

    def w12_sla(self) -> Tuple[str, str]:
        base = f"{self._base()} AND resolved >= \"-7d\""
        return (f"{base} AND created >= \"-{self._thr()}d\"",
                f"{base} AND created <= \"-{self._thr()}d\"")

    def w14_created_vs_resolved(self) -> Tuple[str, str]:
        return (f"{self._base()} AND created >= \"-7d\"",
                f"{self._base()} AND resolved >= \"-7d\"")

    def w15_w16_monthly_candidates(self, year: int, month: int) -> str:
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        return (
            f"{self._base()} AND created >= \"{start}\" AND created < \"{end}\""
            f" ORDER BY created ASC"
        )
