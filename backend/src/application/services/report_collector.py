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

        sla_field_ids = await self._jira.get_sla_field_ids()
        logger.info(f"SLA 필드 목록: {list(sla_field_ids.keys())}")

        results = await asyncio.gather(
            self._collect_w1(q),
            self._simple("개발 SLA 지연", q.w2_dev_sla()),
            self._simple("TAC & QA SLA 지연", q.w3_tac_qa_sla()),
            self._simple("연구소 대기(담당자 미지정)", q.w4_lab_unassigned()),
            self._breakdown("유형별 SLA 지연", q.w5_by_type()),
            self._breakdown("상태별 SLA 지연", q.w6_by_status()),
            self._breakdown("SLA 지연 사유", q.w7_reason_pie()),
            self._simple(f"{now.year}년 누적 생성", q.w8_yearly_created()),
            self._simple(f"{now.year}년 누적 해결", q.w9_yearly_resolved()),
            self._collect_w10(q),
            self._collect_w11(q),
            self._collect_w12(q),
            self._collect_w14(q),
            self._collect_w15_w16_monthly(q, sla_field_ids, now),
        )

        *base_results, (w15_result, w16_result) = results

        widget_ids = [
            WidgetId.OVERDUE_ISSUES,
            WidgetId.DEV_SLA_DELAY,
            WidgetId.TAC_QA_SLA_DELAY,
            WidgetId.LAB_UNASSIGNED,
            WidgetId.SLA_DELAY_BY_TYPE,
            WidgetId.SLA_DELAY_BY_STATUS,
            WidgetId.SLA_DELAY_REASON,
            WidgetId.YEARLY_CREATED,
            WidgetId.YEARLY_RESOLVED,
            WidgetId.AVG_RESOLUTION_TYPE,
            WidgetId.RESOLUTION_REPORT,
            WidgetId.SLA_MET_VS_VIOLATED,
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

    # ──────────────────────────────────────────────────
    # W15 + W16: 최근 6개월 월별 SLA 달성률 시계열
    # breakdown 구조:
    # {
    #   "monthly": [
    #     {"month": "1월", "year": 2026, "month_num": 1,
    #      "rate": 87.5, "met": 7, "total": 8},
    #     ...
    #   ]
    # }
    # ──────────────────────────────────────────────────
    async def _collect_w15_w16_monthly(
        self, q, sla_field_ids: dict[str, str], now: datetime
    ) -> tuple[WidgetResult, WidgetResult]:
        if not sla_field_ids:
            logger.warning("SLA 필드를 찾지 못했습니다. W15/W16를 에러 상태로 반환합니다.")
            empty = WidgetResult(
                name="SLA (필드 미발견)", total=0,
                breakdown={"monthly": [], "error": "SLA 필드 미발견"}
            )
            return empty, empty

        months = self._last_six_months(now)
        sla_field_list = list(sla_field_ids.values())
        fields_str = "summary,issuetype,created,resolutiondate," + ",".join(sla_field_list)

        async def _fetch_month(year: int, month: int):
            jql = q.w15_w16_monthly_candidates(year, month)
            issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)
            return year, month, issues

        month_data = await asyncio.gather(*[_fetch_month(y, m) for y, m in months])

        initial_keywords  = self._settings.sla_initial_response_field_keywords
        resolution_keywords = self._settings.sla_resolution_field_keywords

        def _calc_monthly(issues: list, keywords: list[str]) -> dict[str, int]:
            met = 0
            breached = 0
            for issue in issues:
                f = issue.get("fields") or {}
                for field_name, field_id in sla_field_ids.items():
                    if not any(kw.lower() in field_name.lower() for kw in keywords):
                        continue
                    sla_val = f.get(field_id)
                    if not sla_val:
                        continue
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

        def _build_monthly_result(
            month_data_list, keywords: list[str], widget_name: str, fallback_all: bool = False
        ) -> WidgetResult:
            monthly = []
            total_met = 0
            total_all = 0

            for year, month, issues in month_data_list:
                counts = _calc_monthly(issues, keywords)

                if fallback_all and counts["met"] == 0 and counts["breached"] == 0:
                    merged: dict[str, int] = {"met": 0, "breached": 0}
                    for issue in issues:
                        f = issue.get("fields") or {}
                        for field_id in sla_field_ids.values():
                            sla_val = f.get(field_id)
                            if not sla_val:
                                continue
                            for cycle in sla_val.get("completedCycles") or []:
                                if cycle.get("breached"):
                                    merged["breached"] += 1
                                else:
                                    merged["met"] += 1
                            ongoing = sla_val.get("ongoingCycle")
                            if ongoing:
                                if ongoing.get("breached"):
                                    merged["breached"] += 1
                                else:
                                    merged["met"] += 1
                    counts = merged

                t = counts["met"] + counts["breached"]
                rate = round(counts["met"] / t * 100, 1) if t > 0 else 0.0
                monthly.append({
                    "month": f"{month}월",
                    "year": year,
                    "month_num": month,
                    "rate": rate,
                    "met": counts["met"],
                    "total": t,
                })
                total_met += counts["met"]
                total_all += t

            overall_rate = round(total_met / total_all * 100, 1) if total_all > 0 else 0.0
            logger.info(f"[{widget_name}] 6개월 종합 {overall_rate}% ({total_met}/{total_all})")
            return WidgetResult(
                name=widget_name,
                total=total_all,
                breakdown={"monthly": monthly},
            )

        w15 = _build_monthly_result(
            month_data, initial_keywords, "초기 대응 SLA (최근 6개월)"
        )
        w16 = _build_monthly_result(
            month_data, resolution_keywords, "해결시간 SLA (최근 6개월)", fallback_all=True
        )
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

    # ──────────────────────────────────────────────────
    # 기존 collectors
    # ──────────────────────────────────────────────────
    async def _collect_w1(self, q) -> WidgetResult:
        jql = q.w1_overdue()
        issues = await self._jira.get_issues(jql, max_results=500, fields="issuetype,status")
        total = len(issues)
        breakdown: dict[str, Any] = {}
        for issue in issues:
            f = issue.get("fields", {})
            itype = (f.get("issuetype") or {}).get("name", "기타")
            st = (f.get("status") or {}).get("name", "기타")
            breakdown.setdefault(itype, {})
            breakdown[itype][st] = breakdown[itype].get(st, 0) + 1
        logger.info(f"[W1] {total}건")
        return WidgetResult(name="생성 1달 이상 된 이슈", total=total, jql=jql, breakdown=breakdown)

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
        met_jql, viol_jql = q.w12_sla()
        met, viol = await asyncio.gather(
            self._jira.get_issue_count(met_jql),
            self._jira.get_issue_count(viol_jql),
        )
        logger.info(f"[W12] 만족 {met}건 / 위반 {viol}건")
        return WidgetResult(name="SLA 만족 vs 위반", total=met + viol,
                            breakdown={"SLA 만족": met, "SLA 위반": viol})

    async def _collect_w14(self, q) -> WidgetResult:
        c_jql, r_jql = q.w14_created_vs_resolved()
        c, r = await asyncio.gather(
            self._jira.get_issue_count(c_jql),
            self._jira.get_issue_count(r_jql),
        )
        logger.info(f"[W14] 생성 {c}건 / 해결 {r}건")
        return WidgetResult(name="생성 vs 해결", total=c + r, breakdown={"생성": c, "해결": r})

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
