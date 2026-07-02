# backend/src/application/services/report_collector.py
import logging
from datetime import datetime
from typing import Any

from src.application.services.query_builder import WidgetQueryBuilder
from src.config.settings import Settings
from src.domain.entities.report import Report
from src.domain.entities.widget import WidgetResult
from src.infrastructure.external.jira_client import JiraClient

logger = logging.getLogger(__name__)


class ReportCollector:
    def __init__(self, jira: JiraClient, qb: WidgetQueryBuilder, settings: Settings):
        self._jira = jira
        self._qb = qb
        self._settings = settings

    def collect(self, now: datetime) -> Report:
        q = self._qb.build(now)
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        widgets: dict[str, WidgetResult] = {}
        widgets["w1"] = self._collect_w1(q)
        widgets["w2"] = self._simple("개발 SLA 지연", q.w2_dev_sla())
        widgets["w3"] = self._simple("TAC & QA SLA 지연", q.w3_tac_qa_sla())
        widgets["w4"] = self._simple("연구소 대기(담당자 미지정)", q.w4_lab_unassigned())
        widgets["w5"] = self._breakdown("유형별 SLA 지연", q.w5_by_type())
        widgets["w6"] = self._breakdown("상태별 SLA 지연", q.w6_by_status())
        widgets["w7"] = self._breakdown("SLA 지연 사유", q.w7_reason_pie())
        widgets["w8"] = self._simple("2026년 누적 생성", q.w8_yearly_created())
        widgets["w9"] = self._simple("2026년 누적 해결", q.w9_yearly_resolved())
        widgets["w10"] = self._collect_w10(q)
        widgets["w11"] = self._collect_w11(q)
        widgets["w12"] = self._collect_w12(q)
        widgets["w14"] = self._collect_w14(q)

        logger.info("데이터 수집 완료 ✅")
        return Report(
            id=None,
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets
        )

    def _collect_w1(self, q) -> WidgetResult:
        jql = q.w1_overdue()
        total = self._jira.get_issue_count(jql)
        breakdown: dict[str, Any] = {}
        for itype, sq in q.w1_by_type_status().items():
            breakdown[itype] = {}
            for st, qstr in sq.items():
                c = self._jira.get_issue_count(qstr)
                if c > 0:
                    breakdown[itype][st] = c
        logger.info(f"[W1] {total}건")
        return WidgetResult(name="생성 1달 이상 된 이슈", total=total, jql=jql, breakdown=breakdown)

    def _collect_w10(self, q) -> WidgetResult:
        jql = q.w10_11_resolved()
        issues = self._jira.get_issues(
            jql, max_results=200,
            fields="summary,issuetype,created,resolutiondate"
        )
        type_hours: dict[str, list[float]] = {}
        for issue in issues:
            f = issue.get("fields", {})
            itype = (f.get("issuetype") or {}).get("name", "기타")
            c_str, r_str = f.get("created"), f.get("resolutiondate")
            if not c_str or not r_str:
                continue
            hours = (datetime.fromisoformat(r_str[:19]) - datetime.fromisoformat(c_str[:19])).total_seconds() / 3600
            type_hours.setdefault(itype, []).append(round(hours, 2))

        breakdown: dict[str, Any] = {}
        for itype, hl in type_hours.items():
            avg = sum(hl) / len(hl)
            breakdown[itype] = {"avg_days": round(avg / 24, 1), "avg_hours": round(avg, 1), "count": len(hl)}
        total = sum(d["count"] for d in breakdown.values())
        logger.info(f"[W10] {total}건")
        return WidgetResult(name="유형별 평균 처리일", total=total, jql=jql, breakdown=breakdown)

    def _collect_w11(self, q) -> WidgetResult:
        jql = q.w10_11_resolved()
        issues = self._jira.get_issues(
            jql, max_results=200,
            fields="summary,issuetype,created,resolutiondate"
        )
        resolution_list, breached_count, details = [], 0, []
        thr_hours = self._settings.sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            f = issue.get("fields", {})
            c_str, r_str = f.get("created"), f.get("resolutiondate")
            if not c_str or not r_str:
                continue
            hours = round(
                (datetime.fromisoformat(r_str[:19]) - datetime.fromisoformat(c_str[:19])).total_seconds() / 3600, 2
            )
            breached = hours > thr_hours
            resolution_list.append(hours)
            if breached:
                breached_count += 1
            details.append({
                "key": key,
                "summary": f.get("summary", "")[:40],
                "type": (f.get("issuetype") or {}).get("name", ""),
                "resolution_h": hours,
                "res_breached": breached,
            })

        avg = round(sum(resolution_list) / len(resolution_list), 2) if resolution_list else 0
        breakdown: dict[str, Any] = {
            "avg_resolution_hours": avg,
            "avg_resolution_days": round(avg / 24, 1),
            "resolution_breached": breached_count,
            "total_issues": len(resolution_list),
            "issue_details": details[:20],
        }
        logger.info(f"[W11] 평균 {avg}h ({len(resolution_list)}건)")
        return WidgetResult(name="해결시간 보고서", total=len(resolution_list), jql=jql, breakdown=breakdown)

    def _collect_w12(self, q) -> WidgetResult:
        met_jql, viol_jql = q.w12_sla()
        met = self._jira.get_issue_count(met_jql)
        viol = self._jira.get_issue_count(viol_jql)
        logger.info(f"[W12] 만족 {met}건 / 위반 {viol}건")
        return WidgetResult(name="SLA 만족 vs 위반", total=met + viol,
                            breakdown={"SLA 만족": met, "SLA 위반": viol})

    def _collect_w14(self, q) -> WidgetResult:
        c_jql, r_jql = q.w14_created_vs_resolved()
        c = self._jira.get_issue_count(c_jql)
        r = self._jira.get_issue_count(r_jql)
        logger.info(f"[W14] 생성 {c}건 / 해결 {r}건")
        return WidgetResult(name="생성 vs 해결", total=c + r, breakdown={"생성": c, "해결": r})

    def _simple(self, name: str, jql: str) -> WidgetResult:
        total = self._jira.get_issue_count(jql)
        logger.info(f"[{name}] {total}건")
        return WidgetResult(name=name, total=total, jql=jql)

    def _breakdown(self, name: str, queries: dict[str, str]) -> WidgetResult:
        bd, total = {}, 0
        for label, jql in queries.items():
            c = self._jira.get_issue_count(jql)
            if c > 0:
                bd[label] = c
                total += c
        logger.info(f"[{name}] 총 {total}건")
        return WidgetResult(name=name, total=total, breakdown=bd)
