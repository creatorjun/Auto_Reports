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
        logger.info(f"\ub370\uc774\ud130 \uc218\uc9d1 \uc2dc\uc791 ({q.date_start} ~ {q.date_end})")

        results = await asyncio.gather(
            self._collect_w1(q),
            self._simple_with_details("\uc774\uc288 \ub9ac\ubdf0 \uc911", q.w2_issue_review()),
            self._simple_with_details("\uc790\ub8cc \uc694\uccad \uc911", q.w3_data_request()),
            self._simple("\uc5f0\uad6c\uc18c \ub300\uae30(\ub2f4\ub2f9\uc790 \ubbf8\uc9c0\uc815)", q.w4_lab_unassigned()),
            self._breakdown("\uc720\ud615\ubcc4 SLA \uc9c0\uc5f0", q.w5_by_type()),
            self._breakdown("\uc0c1\ud0dc\ubcc4 SLA \uc9c0\uc5f0", q.w6_by_status()),
            self._collect_w7(q),
            self._simple(f"{now.year}\ub144 \ub204\uc801 \uc0dd\uc131", q.w8_yearly_created()),
            self._simple(f"{now.year}\ub144 \ub204\uc801 \ud574\uacb0", q.w9_yearly_resolved()),
            self._collect_w10(q),
            self._collect_w11(q),
            self._collect_w12(q),
            self._simple_with_details("\uacb0\uacfc \ub300\uae30 \uc911", q.w13_result_pending()),
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

        logger.info("\ub370\uc774\ud130 \uc218\uc9d1 \uc644\ub8cc \u2705")
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
            itype  = (f.get("issuetype") or {}).get("name", "\uae30\ud0c0")
            status = (f.get("status")    or {}).get("name", "\uae30\ud0c0")
            c_str  = f.get("created", "")
            r_str  = f.get("resolutiondate")
            summary = f.get("summary", "")[:60]

            if c_str:
                created_dt = datetime.fromisoformat(c_str[:19])
                elapsed_h  = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h  = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0
            resp_status = "\uc885\ub8cc" if r_str else "\uc9c4\ud589 \uc911"

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
        logger.info(f"[W1] {total}\uac74")
        return WidgetResult(
            name="\uc0dd\uc131 1\ub2ec \uc774\uc0c1 \ub41c \uc774\uc288",
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
        breakdown: dict[str, int] = {}
        for issue in issues:
            f      = issue.get("fields", {})
            status = (f.get("status") or {}).get("name", "\uae30\ud0c0")
            breakdown[status] = breakdown.get(status, 0) + 1
        total = len(issues)
        logger.info(f"[W7] SLA \uc704\ubc18 {total}\uac74 / \uc0c1\ud0dc {len(breakdown)}\uc885")
        return WidgetResult(
            name="SLA \uc9c0\uc5f0 \uc0ac\uc720",
            total=total,
            jql=jql,
            breakdown=breakdown
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
                "type":         (f.get("issuetype") or {}).get("name", "\uae30\ud0c0"),
                "status":       (f.get("status")    or {}).get("name", "\uae30\ud0c0"),
                "created":      c_str[:16].replace("T", " "),
                "elapsed_days": elapsed_days,
            })
        details.sort(key=lambda x: x["elapsed_days"], reverse=True)
        total = len(details)
        logger.info(f"[{name}] {total}\uac74")
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
                "type":    (f.get("issuetype") or {}).get("name", "\uae30\ud0c0"),
                "status":  (f.get("status")    or {}).get("name", "\uae30\ud0c0"),
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
                "type":     (f.get("issuetype") or {}).get("name", "\uae30\ud0c0"),
                "resolved": r_str[:16].replace("T", " "),
            })
        resolved_details.sort(key=lambda x: x["resolved"], reverse=True)

        logger.info(f"[W14] \uc0dd\uc131 {c_count}\uac74 / \ud574\uacb0 {r_count}\uac74")
        return WidgetResult(
            name="\uc0dd\uc131 vs \ud574\uacb0",
            total=c_count + r_count,
            breakdown={
                "\uc0dd\uc131":           c_count,
                "\ud574\uacb0":           r_count,
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
                    "month":     f"{month}\uc6d4",
                    "year":      year,
                    "month_num": month,
                    "rate":      rate,
                    "met":       counts["met"],
                    "total":     t,
                })
                total_met += counts["met"]
                total_all += t
            overall_rate = round(total_met / total_all * 100, 1) if total_all > 0 else 0.0
            logger.info(f"[{widget_name}] field={field_id} 6\uac1c\uc6d4 \uc885\ud569 {overall_rate}% ({total_met}/{total_all})")
            return WidgetResult(name=widget_name, total=total_all, breakdown={"monthly": monthly})

        w15 = _build_monthly_result(month_data, w15_fid, "\ucd5c\ucd08 \uc751\ub2f5 SLA (\ucd5c\uadfc 6\uac1c\uc6d4)")
        w16 = _build_monthly_result(month_data, w16_fid, "\ud574\uacb0\uc2dc\uac04 SLA (\ucd5c\uadfc 6\uac1c\uc6d4)")
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
            itype = (f.get("issuetype") or {}).get("name", "\uae30\ud0c0")
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
        logger.info(f"[W10] {total}\uac74")
        return WidgetResult(name="\uc720\ud615\ubcc4 \ud3c9\uade0 \ucc98\ub9ac\uc77c", total=total, jql=jql, breakdown=breakdown)

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
        logger.info(f"[W11] \ud3c9\uade0 {avg}h ({len(resolution_list)}\uac74)")
        return WidgetResult(name="\ud574\uacb0\uc2dc\uac04 \ubcf4\uace0\uc11c", total=len(resolution_list), jql=jql, breakdown=breakdown)

    async def _collect_w12(self, q) -> WidgetResult:
        met_jql, viol_jql = q.w12_sla()
        met, viol = await asyncio.gather(
            self._jira.get_issue_count(met_jql),
            self._jira.get_issue_count(viol_jql),
        )
        logger.info(f"[W12] \ub9cc\uc871 {met}\uac74 / \uc704\ubc18 {viol}\uac74")
        return WidgetResult(
            name="SLA \ub9cc\uc871 vs \uc704\ubc18",
            total=met + viol,
            breakdown={"SLA \ub9cc\uc871": met, "SLA \uc704\ubc18": viol}
        )

    async def _simple(self, name: str, jql: str) -> WidgetResult:
        total = await self._jira.get_issue_count(jql)
        logger.info(f"[{name}] {total}\uac74")
        return WidgetResult(name=name, total=total, jql=jql)

    async def _breakdown(self, name: str, queries: dict[str, str]) -> WidgetResult:
        labels = list(queries.keys())
        counts = await asyncio.gather(*[self._jira.get_issue_count(jql) for jql in queries.values()])
        bd = {label: cnt for label, cnt in zip(labels, counts) if cnt > 0}
        total = sum(bd.values())
        logger.info(f"[{name}] \uc758 {total}\uac74")
        return WidgetResult(name=name, total=total, breakdown=bd)
