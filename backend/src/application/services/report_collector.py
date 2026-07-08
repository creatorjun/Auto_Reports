# backend/src/application/services/report_collector.py
import asyncio
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

from src.application.services.query_builder import WidgetQueryBuilder
from src.config.settings import Settings
from src.domain.entities.report import Report
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import (
    BreakdownWidgetData,
    CreatedResolvedIssueDetail,
    CreatedVsResolvedWidgetData,
    IssueDetail,
    MonthlyEntry,
    OverdueIssueDetail,
    OverdueWidgetData,
    RecentIssueDetail,
    RecentIssueWidgetData,
    ResolutionTypeEntry,
    ResolutionTypeWidgetData,
    ResolvedIssueDetail,
    SimpleIssueWidgetData,
    SlaDelayWidgetData,
    SlaDistributionEntry,
    SlaMetVsViolatedEntry,
    SlaMetVsViolatedWidgetData,
    SlaMonthlyWidgetData,
    SlaViolatedIssueDetail,
)
from src.domain.ports.jira_port import JiraPort
from src.domain.value_objects.widget_id import WidgetId

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")

STATUS_ORDER = [
    "할 일",
    "이슈 리뷰 중",
    "연구소 대기 중",
    "연구소 검토 중",
    "구현 중",
    "배포 파일 검토 중",
    "자료 요청 중",
    "결과 대기 중",
    "보류 중",
    "영업본부 검토중",
]


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
        widgets[WidgetId.SLA_INITIAL_RESPONSE] = w15_result
        widgets[WidgetId.SLA_RESOLUTION_MONTHLY] = w16_result

        logger.info("데이터 수집 완료 ✅")
        return Report(
            id=None,
            week_start=q.week_start.date(),
            week_end=q.week_end.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
            widgets=widgets,
        )

    async def _collect_w1(self, q) -> WidgetResult[OverdueWidgetData]:
        jql = q.w1_overdue()
        issues = await self._jira.get_issues(
            jql,
            max_results=500,
            fields="summary,issuetype,status,created,resolutiondate",
        )
        total = len(issues)
        by_type: dict[str, dict[str, int]] = {}
        details: list[OverdueIssueDetail] = []
        now_ts = datetime.now()
        thr_hours = self._settings.sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            status = (fields.get("status") or {}).get("name", "기타")
            created = fields.get("created", "")
            resolved = fields.get("resolutiondate")
            summary = fields.get("summary", "")[:60]

            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_h = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0
            response_status = "종료" if resolved else "진행 중"

            by_type.setdefault(issue_type, {})
            by_type[issue_type][status] = by_type[issue_type].get(status, 0) + 1

            details.append(
                OverdueIssueDetail(
                    key=key,
                    summary=summary,
                    type=issue_type,
                    created=created[:16].replace("T", " ") if created else "",
                    resp_status=response_status,
                    over_h=over_h,
                )
            )

        details.sort(key=lambda item: item.over_h, reverse=True)
        logger.info(f"[W1] {total}건")
        return WidgetResult(
            name="생성 1달 이상 된 이슈",
            total=total,
            jql=jql,
            data=OverdueWidgetData(by_type=by_type, issue_details=details),
        )

    async def _collect_w7(self, q) -> WidgetResult[SlaDelayWidgetData]:
        jql = q.w7_sla_violated()
        issues = await self._jira.get_issues(
            jql,
            max_results=500,
            fields="summary,issuetype,status,created",
        )
        by_status: dict[str, int] = {}
        details: list[SlaViolatedIssueDetail] = []
        now_ts = datetime.now()
        thr_hours = self._settings.sla_threshold_days * 24

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            status = (fields.get("status") or {}).get("name", "기타")
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created", "")

            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_h = round((now_ts - created_dt).total_seconds() / 3600, 1)
            else:
                elapsed_h = 0.0

            over_h = round(elapsed_h - thr_hours, 1) if elapsed_h > thr_hours else 0.0

            by_status[status] = by_status.get(status, 0) + 1
            details.append(
                SlaViolatedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=issue_type,
                    status=status,
                    created=created[:16].replace("T", " ") if created else "",
                    over_h=over_h,
                )
            )

        total = len(issues)
        details.sort(key=lambda item: item.over_h, reverse=True)
        distribution = [
            SlaDistributionEntry(
                status=status,
                count=count,
                rate=round(count / total * 100, 1) if total > 0 else 0.0,
            )
            for status, count in sorted(by_status.items(), key=lambda item: item[1], reverse=True)
        ]

        logger.info(f"[W7] SLA 위반 {total}건 / 상태 {len(by_status)}종")
        return WidgetResult(
            name="SLA 지연 사유",
            total=total,
            jql=jql,
            data=SlaDelayWidgetData(
                by_status=dict(sorted(by_status.items(), key=lambda item: item[1], reverse=True)),
                distribution=distribution,
                issue_details=details,
            ),
        )

    async def _simple_with_details(self, name: str, jql: str) -> WidgetResult[SimpleIssueWidgetData]:
        issues = await self._jira.get_issues(
            jql,
            max_results=200,
            fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        details: list[IssueDetail] = []
        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            created = fields.get("created") or ""
            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_days = (now_ts - created_dt).days
            else:
                elapsed_days = 0
            details.append(
                IssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    status=(fields.get("status") or {}).get("name", "기타"),
                    created=created[:16].replace("T", " "),
                    elapsed_days=elapsed_days,
                )
            )
        details.sort(key=lambda item: item.elapsed_days, reverse=True)
        total = len(details)
        logger.info(f"[{name}] {total}건")
        return WidgetResult(
            name=name,
            total=total,
            jql=jql,
            data=SimpleIssueWidgetData(issue_details=details),
        )

    async def _collect_w11(self, q) -> WidgetResult[RecentIssueWidgetData]:
        jql = q.w11_recent()
        issues = await self._jira.get_issues(
            jql,
            max_results=15,
            fields="summary,issuetype,status,created",
        )
        now_ts = datetime.now()
        details: list[RecentIssueDetail] = []

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            status = (fields.get("status") or {}).get("name", "기타")
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created") or ""
            elapsed_days = 0
            if created:
                created_dt = datetime.fromisoformat(created[:19])
                elapsed_days = (now_ts - created_dt).days
            stage_index = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
            details.append(
                RecentIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:50],
                    type=issue_type,
                    status=status,
                    stage_index=stage_index,
                    created=created[:16].replace("T", " ") if created else "",
                    elapsed_days=elapsed_days,
                )
            )

        total = len(details)
        logger.info(f"[W11] 최근 생성 {total}건")
        return WidgetResult(
            name="최근 이슈 현황",
            total=total,
            jql=jql,
            data=RecentIssueWidgetData(issue_details=details),
        )

    async def _collect_w14(self, q) -> WidgetResult[CreatedVsResolvedWidgetData]:
        created_jql, resolved_jql = q.w14_created_vs_resolved()

        created_count_task = self._jira.get_issue_count(created_jql)
        resolved_count_task = self._jira.get_issue_count(resolved_jql)
        created_issues_task = self._jira.get_issues(
            created_jql,
            max_results=200,
            fields="summary,issuetype,status,created",
        )
        resolved_issues_task = self._jira.get_issues(
            resolved_jql,
            max_results=200,
            fields="summary,issuetype,resolutiondate",
        )
        created_count, resolved_count, created_issues, resolved_issues = await asyncio.gather(
            created_count_task,
            resolved_count_task,
            created_issues_task,
            resolved_issues_task,
        )

        created_details: list[CreatedResolvedIssueDetail] = []
        for issue in created_issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            created_details.append(
                CreatedResolvedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    created=(fields.get("created") or "")[:16].replace("T", " "),
                )
            )
        created_details.sort(key=lambda item: item.created, reverse=True)

        resolved_details: list[ResolvedIssueDetail] = []
        for issue in resolved_issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            resolved = fields.get("resolutiondate") or ""
            resolved_details.append(
                ResolvedIssueDetail(
                    key=key,
                    summary=fields.get("summary", "")[:60],
                    type=(fields.get("issuetype") or {}).get("name", "기타"),
                    resolved=resolved[:16].replace("T", " "),
                )
            )
        resolved_details.sort(key=lambda item: item.resolved, reverse=True)

        logger.info(f"[W14] 생성 {created_count}건 / 해결 {resolved_count}건")
        return WidgetResult(
            name="생성 vs 해결",
            total=created_count + resolved_count,
            data=CreatedVsResolvedWidgetData(
                created=created_count,
                resolved=resolved_count,
                created_details=created_details,
                resolved_details=resolved_details,
            ),
        )

    async def _collect_w15_w16_monthly(
        self,
        q,
        now: datetime,
    ) -> tuple[WidgetResult[SlaMonthlyWidgetData], WidgetResult[SlaMonthlyWidgetData]]:
        w15_fid = self._settings.sla_initial_response_field_id
        w16_fid = self._settings.sla_resolution_field_id
        fields_str = f"summary,issuetype,created,resolutiondate,{w15_fid},{w16_fid}"

        months = self._last_six_months(now)

        async def _fetch_month(year: int, month: int):
            jql = q.w15_w16_monthly_candidates(year, month)
            issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)
            return year, month, issues

        month_data = await asyncio.gather(*[_fetch_month(year, month) for year, month in months])

        def _count_sla_cycles(sla_value: dict) -> dict[str, int]:
            met = breached = 0
            for cycle in sla_value.get("completedCycles") or []:
                if cycle.get("breached"):
                    breached += 1
                else:
                    met += 1
            ongoing = sla_value.get("ongoingCycle")
            if ongoing:
                if ongoing.get("breached"):
                    breached += 1
                else:
                    met += 1
            return {"met": met, "breached": breached}

        def _calc_monthly(issues: list, field_id: str) -> dict[str, int]:
            met = breached = 0
            for issue in issues:
                sla_value = (issue.get("fields") or {}).get(field_id)
                if not sla_value:
                    continue
                counts = _count_sla_cycles(sla_value)
                met += counts["met"]
                breached += counts["breached"]
            return {"met": met, "breached": breached}

        def _build_monthly_result(month_data_list, field_id: str, widget_name: str) -> WidgetResult[SlaMonthlyWidgetData]:
            monthly: list[MonthlyEntry] = []
            total_met = 0
            total_all = 0
            for year, month, issues in month_data_list:
                counts = _calc_monthly(issues, field_id)
                total = counts["met"] + counts["breached"]
                rate = round(counts["met"] / total * 100, 1) if total > 0 else 0.0
                monthly.append(
                    MonthlyEntry(
                        month=f"{month}월",
                        year=year,
                        month_num=month,
                        rate=rate,
                        met=counts["met"],
                        total=total,
                    )
                )
                total_met += counts["met"]
                total_all += total
            overall_rate = round(total_met / total_all * 100, 1) if total_all > 0 else 0.0
            logger.info(f"[{widget_name}] field={field_id} 6개월 종합 {overall_rate}% ({total_met}/{total_all})")
            return WidgetResult(
                name=widget_name,
                total=total_all,
                data=SlaMonthlyWidgetData(monthly=monthly),
            )

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

    async def _collect_w10(self, q) -> WidgetResult[ResolutionTypeWidgetData]:
        jql = q.w10_11_resolved()
        issues = await self._jira.get_issues(
            jql,
            max_results=200,
            fields="summary,issuetype,created,resolutiondate",
        )
        type_hours: dict[str, list[float]] = {}
        for issue in issues:
            fields = issue.get("fields", {})
            issue_type = (fields.get("issuetype") or {}).get("name", "기타")
            created = fields.get("created")
            resolved = fields.get("resolutiondate")
            if not created or not resolved:
                continue
            hours = (datetime.fromisoformat(resolved[:19]) - datetime.fromisoformat(created[:19])).total_seconds() / 3600
            type_hours.setdefault(issue_type, []).append(round(hours, 2))

        breakdown: dict[str, ResolutionTypeEntry] = {}
        for issue_type, hour_list in type_hours.items():
            average = sum(hour_list) / len(hour_list)
            breakdown[issue_type] = ResolutionTypeEntry(
                avg_days=round(average / 24, 1),
                avg_hours=round(average, 1),
                count=len(hour_list),
            )
        total = sum(entry.count for entry in breakdown.values())
        logger.info(f"[W10] {total}건")
        return WidgetResult(
            name="유형별 평균 처리일",
            total=total,
            jql=jql,
            data=ResolutionTypeWidgetData(by_type=breakdown),
        )

    async def _collect_w12(self, q) -> WidgetResult[SlaMetVsViolatedWidgetData]:
        w15_fid = self._settings.sla_initial_response_field_id
        w16_fid = self._settings.sla_resolution_field_id
        fields_str = f"summary,issuetype,status,created,resolutiondate,{w15_fid},{w16_fid}"

        jql = q.w12_sla()
        issues = await self._jira.get_issues(jql, max_results=500, fields=fields_str)

        total_violations = 0
        initial_response_violations = 0
        resolution_violations = 0

        for issue in issues:
            fields = issue.get("fields") or {}
            initial_response_sla = fields.get(w15_fid)
            resolution_sla = fields.get(w16_fid)
            initial_response_breached = self._is_sla_breached(initial_response_sla)
            resolution_breached = self._is_sla_breached(resolution_sla)
            if initial_response_sla is not None and initial_response_breached:
                initial_response_violations += 1
            if resolution_sla is not None and resolution_breached:
                resolution_violations += 1
            if (initial_response_sla is not None and initial_response_breached) or (
                resolution_sla is not None and resolution_breached
            ):
                total_violations += 1

        violation_distribution: list[SlaMetVsViolatedEntry] = []
        if total_violations > 0:
            if initial_response_violations > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="최초 응답 SLA",
                        field_id=w15_fid,
                        count=initial_response_violations,
                        rate=round(initial_response_violations / total_violations * 100, 1),
                    )
                )
            if resolution_violations > 0:
                violation_distribution.append(
                    SlaMetVsViolatedEntry(
                        stage="해결 시간 SLA",
                        field_id=w16_fid,
                        count=resolution_violations,
                        rate=round(resolution_violations / total_violations * 100, 1),
                    )
                )

        logger.info(
            f"[W12] 위반 원 {total_violations}건 (최초응답 {initial_response_violations}건 / 해결시간 {resolution_violations}건)"
        )
        return WidgetResult(
            name="SLA 만족 vs 위반",
            total=total_violations,
            jql=jql,
            data=SlaMetVsViolatedWidgetData(
                initial_response_violations=initial_response_violations,
                resolution_violations=resolution_violations,
                violation_distribution=violation_distribution,
            ),
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

    async def _simple(self, name: str, jql: str) -> WidgetResult[None]:
        total = await self._jira.get_issue_count(jql)
        logger.info(f"[{name}] {total}건")
        return WidgetResult(name=name, total=total, jql=jql)

    async def _breakdown(self, name: str, queries: dict[str, str]) -> WidgetResult[BreakdownWidgetData]:
        labels = list(queries.keys())
        counts = await asyncio.gather(*[self._jira.get_issue_count(jql) for jql in queries.values()])
        breakdown = {label: count for label, count in zip(labels, counts) if count > 0}
        total = sum(breakdown.values())
        logger.info(f"[{name}] 의 {total}건")
        return WidgetResult(name=name, total=total, data=BreakdownWidgetData(counts=breakdown))
