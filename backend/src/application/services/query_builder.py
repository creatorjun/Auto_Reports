# backend/src/application/services/query_builder.py
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

    def w2_dev_sla(self) -> str:
        return (f"{self._base()} AND status IN (\"연구소 검토 중\",\"구현 중\",\"배포 파일 검토 중\") "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    def w3_tac_qa_sla(self) -> str:
        return (f"{self._base()} AND status IN (\"할 일\",\"이슈 리뷰 중\",\"자료 요청 중\",\"결과 대기 중\") "
                f"AND created <= \"-{self._thr()}d\" AND updated >= \"-7d\" "
                f"AND status NOT IN ({self._closed()})")

    def w4_lab_unassigned(self) -> str:
        return (f"{self._base()} AND status = \"연구소 대기 중\" AND assignee IS EMPTY "
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
            "TAC 처리 지연": f"{base} AND status IN (\"할 일\",\"이슈 리뷰 중\")",
            "연구소 대기": f"{base} AND status IN (\"연구소 대기 중\",\"연구소 검토 중\")",
            "개발 진행 중": f"{base} AND status IN (\"구현 중\",\"배포 파일 검토 중\")",
            "고객 응답 대기": f"{base} AND status IN (\"자료 요청 중\",\"결과 대기 중\")",
            "보류": f"{base} AND status = \"보류 중\"",
            "영업 검토": f"{base} AND status = \"영업본부 검토중\"",
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

    def w15_initial_response_candidates(self) -> str:
        """최근 30일 생성된 이슈 — 초기 대응 SLA 계산 대상"""
        return f"{self._base()} AND created >= \"-30d\" ORDER BY created ASC"

    def w16_resolution_candidates(self) -> str:
        """최근 30일 생성 후 해결된 이슈 — 해결시간 SLA 계산 대상"""
        return f"{self._base()} AND created >= \"-30d\" AND resolved IS NOT EMPTY ORDER BY created ASC"
