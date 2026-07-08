# backend/src/application/services/report_collector.py
import asyncio
import logging
from datetime import datetime, date
from typing import Any
from zoneinfo import ZoneInfo

from src.application.services.query_builder import WidgetQueryBuilder
from src.config.settings import Settings
from src.domain.entities.report import Report
from src.domain.entities.widget import WidgetResult
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class ReportCollector:
    def __init__(self, jira: JiraPort, qb: WidgetQueryBuilder, settings: Settings):
        self._jira = jira
        self._qb = qb
        self._settings = settings

    async def collect(self, now: datetime) -> Report:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        q = self._qb.build(now)
        logger.info(f"데이터 수집 시작 ({q.date_start} ~ {q.date_end})")

        results = await asyncio.gather(
            self._collect_w1(q),
            self._simple_with_details("이슈 리뷰 중", q.w2_issue_review()),
            self._simple_with_details("자료 요청 중", q.w3_data_request()),
            self._simple("연구소 대기(담당자 미지정)", q.w4_lab_unassigned()),
            self._breakdown("유형별 SLA 지연", q.w5_by_type()),
            self._breakdown("상태별 SLA 지연", q.w6_by_status()),
            self._collect_w7(q),
            self._simple(f"{now.year}년 누적 생성", q.w8_yearly_created()),
            self._simple(f"{now.year}년 누적 해결", q.w9_yearly_resolved()),
            self._collect_w10(q),
            self._collect_w11(q),
            self._collect_w12(q),
            self._simple_with_details("결과 대기 중", q.w13_result_pending()),
            self._collect_w14(q),
            self._collect_w15_w16_monthly(q, now),
        )

        *base_results, (w15_result, w16_result) = results

        widget_ids = [
            WidgetId.OVERDUE_ISSUES,
            WidgetId.ISSUE_REVIEW,
            WidgetId.DATA_REQUEST,
            WidgetId.LAB_UNASSIGNED,
            WidgetId.SLA_DELAY_BY_TYPE,
            WidgetId.SLA_DELAY_BY_STATUS,
            WidgetId.SLA_DELAY_REASON,
            WidgetId.YEARLY_CREATED,
            WidgetId.YEARLY_RESOLVED,
            WidgetId.AVG_RESOLUTION_TYPE,
            WidgetId.RESOLUTION_REPORT,
            WidgetId.SLA_MET_VS_VIOLATED,
            WidgetId.RESULT_PENDING,
            WidgetId.CREATED_VS_RESOLVED,
        ]

        widgets: dict[str, WidgetResult] = dict(zip(widget_ids, base_results))
        widgets[WidgetId.SLA_INITIAL_RESPONSE]   = w15_result
        widgets[WidgetId.SLA_RESOLUTION_MONTHLY] = w16_result

        logger.info("데이터 수집 완료 ✅")
        return Report(
            id=None,
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets
        )

    async def _collect_w1(self, q) -> WidgetResult:
        jql = q.w1_overdue()
        issues = await self._jira.get_issues(
            jql, max_results=500,
            fields="summary,issuetype,status,created,resolutiondate"
        )
        total = len(issues)
        by_type: dict[str, Any] = {}
        details: list[dict] = []
        now_ts = datetime.now()
        thr_hours = self._settings.sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            f   = issue.get("fields", {})
            itype  = (f.get("issuetype") or {}).get("name", "기타")
            status = (f.get("status")    or {}).get("name", "기타")
            c_str  = f.get("created", "")
            r_str  = f.get("resolutiondate")
            summary = f.get("summary", "")[:60]

            if c_str:
                created_dt = datetime.fromisoformat(c_str[:19])
                elapsed_h  = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h  = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0
            resp_status = "종료" if r_str else "진행 중"

            by_type.setdefault(itype, {})
            by_type[itype][status] = by_type[itype].get(status, 0) + 1

            details.append({
                "key":         key,
                "summary":     summary,
                "type":        itype,
                "created":     c_str[:16].replace("T", " ") if c_str else "",
                "resp_status": resp_status,
                "over_h":      over_h,
            })

        details.sort(key=lambda x: x["over_h"], reverse=True)
        logger.info(f"[W1] {total}건")
        return WidgetResult(
            name="생성 1달 이상 된 이슈",
            total=total,
            jql=jql,
            breakdown={"by_type": by_type, "issue_details": details}
        )

    async def _collect_w7(self, q) -> WidgetResult:
        jql = q.w7_sla_violated()
        issues = await self._jira.get_issues(
            jql, max_results=500,
            fields="summary,issuetype,status,created"
        )
        by_status: dict[str, int] = {}
        details: list[dict] = []
        now_ts = datetime.now()
        thr_hours = self._settings.sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            f      = issue.get("fields", {})
            status = (f.get("status") or {}).get("name", "기타")
            itype  = (f.get("issuetype") or {}).get("name", "기타")
            c_str  = f.get("created", "")

            if c_str:
                created_dt = datetime.fromisoformat(c_str[:19])
                elapsed_h  = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0

            by_status[status] = by_status.get(status, 0) + 1
            details.append({
                "key":     key,
                "summary": f.get("summary", "")[:60],
                "type":    itype,
                "status":  status,
                "created": c_str[:16].replace("T", " ") if c_str else "",
                "over_h":  over_h,
            })

        total = len(issues)
        details.sort(key=lambda x: x["over_h"], reverse=True)

        status_distribution: list[dict] = [
            {
                "status": st,
                "count":  cnt,
                "rate":   round(cnt / total * 100, 1) if total > 0 else 0.0,
            }
            for st, cnt in sorted(by_status.items(), key=lambda x: x[1], reverse=True)
        ]

        logger.info(f"[W7] SLA 위반 {total}건 / 상태 {len(by_status)}종")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            breakdown={
                "by_status":           by_status,
                "status_distribution": status_distribution,
                "issue_details":       details,
            }
        )

    async def _simple_with_details(self, name: str, jql: str) -> WidgetResult:
        issues = await self._jira.get_issues(
            jql, max_results=200,
            fields="summary,issuetype,status,created"
        )
        now_ts = datetime.now()
        details: list[dict] = []
        for issue in issues:
            key = issue.get("key", "")
            f   = issue.get("fields", {})
            c_str = f.get("created") or ""
            if c_str:
                created_dt   = datetime.fromisoformat(c_str[:19])
                elapsed_days = (now_ts - created_dt).days
            else:
                elapsed_days = 0
            details.append({
                "key":          key,
                "summary":      f.get("summary", "")[:60],
                "type":         (f.get("issuetype") or {}).get("name", "기타"),
                "status":       (f.get("status")    or {}).get("name", "기타"),
                "created":      c_str[:16].replace("T", " "),
                "elapsed_days": elapsed_days,
            })
        details.sort(key=lambda x: x["elapsed_days"], reverse=True)
        total = len(details)
        logger.info(f"[{name}] {total}건")
        return WidgetResult(
            name=name,
            total=total,
            jql=jql,
            breakdown={"issue_details": details}
        )

    async def _collect_w14(self, q) -> WidgetResult:
        c_jql, r_jql = q.w14_created_vs_resolved()

        c_count_task  = self._jira.get_issue_count(c_jql)
        r_count_task  = self._jira.get_issue_count(r_jql)
        c_issues_task = self._jira.get_issues(
            c_jql, max_results=200,
            fields="summary,issuetype,status,created"
        )
        r_issues_task = self._jira.get_issues(
            r_jql, max_results=200,
            fields="summary,issuetype,resolutiondate"
        )
        c_count, r_count, c_issues, r_issues = await asyncio.gather(
            c_count_task, r_count_task, c_issues_task, r_issues_task
        )

        created_details: list[dict] = []
        for issue in c_issues:
            key = issue.get("key", "")
            f   = issue.get("fields", {})
            created_details.append({
                "key":     key,
                "summary": f.get("summary", "")[:60],
                "type":    (f.get("issuetype") or {}).get("name", "기타"),
                "status":  (f.get("status")    or {}).get("name", "기타"),
                "created": (f.get("created") or "")[:16].replace("T", " "),
            })
        created_details.sort(key=lambda x: x["created"], reverse=True)

        resolved_details: list[dict] = []
        for issue in r_issues:
            key = issue.get("key", "")
            f   = issue.get("fields", {})
            r_str = f.get("resolutiondate") or ""
            resolved_details.append({
                "key":      key,
                "summary":  f.get("summary", "")[:60],
                "type":     (f.get("issuetype") or {}).get("name", "기타"),
                "resolved": r_str[:16].replace("T", " "),
            })
        resolved_details.sort(key=lambda x: x["resolved"], reverse=True)

        logger.info(f"[W14] 생성 {c_count}건 / 해결 {r_count}건")
        return WidgetResult(
            name="생성 vs 해결",
            total=c_count + r_count,
            breakdown={
                "생성":           c_count,
                "해결":           r_count,
                "created_details":  created_details,
                "resolved_details": resolved_details,
            }
        )

    async def _collect_w15_w16_monthly(
        self, q, now: datetime
    ) -> tuple[WidgetResult, WidgetResult]:
        w15_fid = self._settings.sla_initial_response_field_id
        w16_fid = self._settings.sla_resolution_field_id
        fields_str = f"summary,issuetype,created,resolutiondate,{w15_fid},{w16_fid}"

        months = self._last_six_months(now)

        async def _fetch_month(year: int, month: int):
            jql = q.w15_w16_monthly_candidates(year, month)
            issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)
            return year, month, issues

        month_data = await asyncio.gather(*[_fetch_month(y, m) for y, m in months])

        def _count_sla_cycles(sla_val: dict) -> dict[str, int]:
            met = breached = 0
            for cycle in sla_val.get("completedCycles") or []:
                if cycle.get("breached"):
                    breached += 1
                else:
                    met += 1
            ongoing = sla_val.get("ongoingCycle")
            if ongoing:
                if ongoing.get("breached"):
                    breached += 1
                else:
                    met += 1
            return {"met": met, "breached": breached}

        def _calc_monthly(issues: list, field_id: str) -> dict[str, int]:
            met = breached = 0
            for issue in issues:
                sla_val = (issue.get("fields") or {}).get(field_id)
                if not sla_val:
                    continue
                counts    = _count_sla_cycles(sla_val)
                met      += counts["met"]
                breached += counts["breached"]
            return {"met": met, "breached": breached}

        def _build_monthly_result(month_data_list, field_id: str, widget_name: str) -> WidgetResult:
            monthly   = []
            total_met = 0
            total_all = 0
            for year, month, issues in month_data_list:
                counts = _calc_monthly(issues, field_id)
                t      = counts["met"] + counts["breached"]
                rate   = round(counts["met"] / t * 100, 1) if t > 0 else 0.0
                monthly.append({
                    "month":     f"{month}월",
                    "year":      year,
                    "month_num": month,
                    "rate":      rate,
                    "met":       counts["met"],
                    "total":     t,
                })
                total_met += counts["met"]
                total_all += t
            overall_rate = round(total_met / total_all * 100, 1) if total_all > 0 else 0.0
            logger.info(f"[{widget_name}] field={field_id} 6개월 종합 {overall_rate}% ({total_met}/{total_all})")
            return WidgetResult(name=widget_name, total=total_all, breakdown={"monthly": monthly})

        w15 = _build_monthly_result(month_data, w15_fid, "최초 응답 SLA (최근 6개월)")
        w16 = _build_monthly_result(month_data, w16_fid, "해결시간 SLA (최근 6개월)")
        return w15, w16

    @staticmethod
    def _last_six_months(now: datetime) -> list[tuple[int, int]]:
        result = []
        year, month = now.year, now.month
        for _ in range(6):
            result.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return list(reversed(result))

    async def _collect_w10(self, q) -> WidgetResult:
        jql = q.w10_11_resolved()
        issues = await self._jira.get_issues(
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

    async def _collect_w11(self, q) -> WidgetResult:
        jql = q.w10_11_resolved()
        issues = await self._jira.get_issues(
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

    async def _collect_w12(self, q) -> WidgetResult:
        w15_fid = self._settings.sla_initial_response_field_id
        w16_fid = self._settings.sla_resolution_field_id
        fields_str = f"summary,issuetype,status,created,resolutiondate,{w15_fid},{w16_fid}"

        jql = q.w12_sla()
        issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)

        total_met = total_viol = 0
        ir_met = ir_viol = 0
        res_met = res_viol = 0

        for issue in issues:
            f = issue.get("fields") or {}

            ir_sla  = f.get(w15_fid)
            res_sla = f.get(w16_fid)

            ir_breached  = self._is_sla_breached(ir_sla)
            res_breached = self._is_sla_breached(res_sla)

            if ir_sla is not None:
                if ir_breached:
                    ir_viol += 1
                else:
                    ir_met += 1

            if res_sla is not None:
                if res_breached:
                    res_viol += 1
                else:
                    res_met += 1

            violated = (ir_sla is not None and ir_breached) or (res_sla is not None and res_breached)
            if violated:
                total_viol += 1
            elif ir_sla is not None or res_sla is not None:
                total_met += 1

        grand_total = total_met + total_viol

        ir_total  = ir_met  + ir_viol
        res_total = res_met + res_viol

        violation_distribution: list[dict] = []
        if total_viol > 0:
            if ir_viol > 0:
                violation_distribution.append({
                    "stage":       "최초 응답 SLA",
                    "field_id":    w15_fid,
                    "count":       ir_viol,
                    "rate":        round(ir_viol / total_viol * 100, 1),
                })
            if res_viol > 0:
                violation_distribution.append({
                    "stage":       "해결 시간 SLA",
                    "field_id":    w16_fid,
                    "count":       res_viol,
                    "rate":        round(res_viol / total_viol * 100, 1),
                })

        logger.info(
            f"[W12] 만족 {total_met}건 / 위반 {total_viol}건 "
            f"(최초응답 위반 {ir_viol}/{ir_total} / 해결시간 위반 {res_viol}/{res_total})"
        )
        return WidgetResult(
            name="SLA 만족 vs 위반",
            total=grand_total,
            jql=jql,
            breakdown={
                "SLA 만족":               total_met,
                "SLA 위반":               total_viol,
                "최초_응답_만족":          ir_met,
                "최초_응답_위반":          ir_viol,
                "해결_시간_만족":          res_met,
                "해결_시간_위반":          res_viol,
                "violation_distribution": violation_distribution,
            }
        )

    @staticmethod
    def _is_sla_breached(sla_val: dict | None) -> bool:
        if not sla_val:
            return False
        for cycle in sla_val.get("completedCycles") or []:
            if cycle.get("breached"):
                return True
        ongoing = sla_val.get("ongoingCycle")
        if ongoing and ongoing.get("breached"):
            return True
        return False

    async def _simple(self, name: str, jql: str) -> WidgetResult:
        total = await self._jira.get_issue_count(jql)
        logger.info(f"[{name}] {total}건")
        return WidgetResult(name=name, total=total, jql=jql)

    async def _breakdown(self, name: str, queries: dict[str, str]) -> WidgetResult:
        labels = list(queries.keys())
        counts = await asyncio.gather(*[self._jira.get_issue_count(jql) for jql in queries.values()])
        bd = {label: cnt for label, cnt in zip(labels, counts) if cnt > 0}
        total = sum(bd.values())
        logger.info(f"[{name}] 의 {total}건")
        return WidgetResult(name=name, total=total, breakdown=bd)
