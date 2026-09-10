# backend/tests/test_report_period_end.py
import datetime
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.jira_port import JiraIssue, JiraIssueField
from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.count_collector import TypeCountCollector
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.application.widgets.resolution_collector import ResolutionCollector


KST = datetime.timezone(datetime.timedelta(hours=9))


def query_builder() -> WidgetQueryBuilder:
    return WidgetQueryBuilder(QueryConfig(
        project_key="TACEA",
        issue_types=["인시던트"],
        active_statuses=["처리 중"],
        closed_statuses=["Closed"],
        sla_threshold_days=30,
        year_start=2026,
    ))


def issue(key: str, created: str, resolved: str) -> JiraIssue:
    return JiraIssue(
        key=key,
        summary=key,
        issue_type="인시던트",
        status="Closed",
        created=f"{created}.000+0900",
        resolved=f"{resolved}.000+0900",
    )


class DateRangeJira:
    def __init__(self, issues: list[JiraIssue]) -> None:
        self.issues = issues
        self.requested_limits: list[int | None] = []

    async def get_issues(
        self,
        jql: str,
        max_results: int | None,
        fields: frozenset[JiraIssueField],
    ) -> list[JiraIssue]:
        self.requested_limits.append(max_results)
        conditions = re.findall(r'(created|resolved)\s*(>=|<=|<|>)\s*"(\d{4}-\d{2}-\d{2})"', jql)
        if len(conditions) != 2:
            raise AssertionError(f"Expected a bounded date range: {jql}")
        matches = []
        for entry in self.issues:
            included = True
            for field, operator, date in conditions:
                actual = datetime.datetime.fromisoformat(getattr(entry, field))
                bound = datetime.datetime.fromisoformat(date).replace(tzinfo=KST)
                included = included and {
                    ">=": actual >= bound,
                    "<=": actual <= bound,
                    "<": actual < bound,
                    ">": actual > bound,
                }[operator]
            if included:
                matches.append(entry)
        return matches if max_results is None else matches[:max_results]


class ReportPeriodEndQueryTest(unittest.TestCase):
    def test_period_queries_cover_same_day_month_year_and_leap_day_boundaries(self) -> None:
        for start, end, next_day in [
            ("2026-09-10", "2026-09-10", "2026-09-11"),
            ("2026-08-01", "2026-08-31", "2026-09-01"),
            ("2026-01-01", "2026-12-31", "2027-01-01"),
            ("2024-02-01", "2024-02-29", "2024-03-01"),
            ("2026-02-01", "2026-02-28", "2026-03-01"),
        ]:
            with self.subTest(start=start, end=end):
                start_at = datetime.datetime.fromisoformat(start).replace(tzinfo=KST)
                end_at = datetime.datetime.fromisoformat(end).replace(tzinfo=KST)
                queries = query_builder().build(end_at, week_start_override=start_at)
                created, resolved = queries.w3_created_vs_resolved()
                for field, jql in [
                    ("created", created),
                    ("resolved", resolved),
                    ("resolved", queries.w14_resolution_resolved()),
                ]:
                    self.assertIn(f'{field} >= "{start}"', jql)
                    self.assertIn(f'{field} < "{next_day}"', jql)
                    self.assertNotIn("<=", jql)
                self.assertEqual(start, queries.date_start)
                self.assertEqual(end, queries.date_end)
                self.assertEqual(start_at, queries.week_start)
                self.assertEqual(end_at, queries.week_end)

    def test_end_time_does_not_change_the_inclusive_calendar_date(self) -> None:
        start_at = datetime.datetime(2026, 9, 1, tzinfo=KST)
        for hour, minute, second in [(0, 0, 0), (12, 30, 0), (23, 59, 59)]:
            with self.subTest(time=(hour, minute, second)):
                end_at = datetime.datetime(2026, 9, 10, hour, minute, second, tzinfo=KST)
                queries = query_builder().build(end_at, week_start_override=start_at)
                created, resolved = queries.w3_created_vs_resolved()
                self.assertIn('created < "2026-09-11"', created)
                self.assertIn('resolved < "2026-09-11"', resolved)
                self.assertEqual(end_at, queries.week_end)
                self.assertEqual("2026-09-10", queries.date_end)

    def test_default_week_keeps_its_displayed_seven_days(self) -> None:
        end_at = datetime.datetime(2026, 9, 10, 23, 59, 59, tzinfo=KST)
        queries = query_builder().build(end_at)

        self.assertEqual("2026-09-04", queries.date_start)
        self.assertEqual("2026-09-10", queries.date_end)
        self.assertIn('created >= "2026-09-04"', queries.w3_created_vs_resolved()[0])
        self.assertIn('created < "2026-09-11"', queries.w3_created_vs_resolved()[0])

    def test_full_year_detail_queries_match_annual_aggregate_queries(self) -> None:
        for year in [2024, 2025, 2026]:
            with self.subTest(year=year):
                queries = query_builder().build(
                    datetime.datetime(year, 12, 31, 23, 59, 59, tzinfo=KST),
                    week_start_override=datetime.datetime(year, 1, 1, tzinfo=KST),
                )
                self.assertEqual(
                    (queries.w1_yearly_created(), queries.w2_yearly_resolved()),
                    queries.w3_created_vs_resolved(),
                )
                self.assertEqual(
                    f"{queries.w2_yearly_resolved()} ORDER BY resolved DESC",
                    queries.w14_resolution_resolved(),
                )


class ReportPeriodEndCollectorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime.datetime(2026, 9, 10, tzinfo=KST)
        self.queries = query_builder().build(
            self.now,
            week_start_override=datetime.datetime(2026, 9, 1, tzinfo=KST),
        )
        self.jira = DateRangeJira([
            issue("BEFORE", "2026-08-31T23:59:59", "2026-08-31T23:59:59"),
            issue("OLD-CREATED", "2026-08-31T23:59:59", "2026-09-01T00:00:00"),
            issue("START", "2026-09-01T00:00:00", "2026-09-01T00:00:00"),
            issue("END", "2026-09-10T23:59:59", "2026-09-10T23:59:59"),
            issue("NEXT-DAY", "2026-09-11T00:00:00", "2026-09-11T00:00:00"),
            issue("LATER-RESOLVED", "2026-09-10T12:00:00", "2026-09-11T00:00:00"),
        ])

    async def test_created_and_resolved_details_include_end_day_and_exclude_next_day(self) -> None:
        result = await CreatedVsResolvedCollector(self.jira, self.queries).collect()

        self.assertEqual(3, result.total)
        self.assertEqual(3, result.data.created)
        self.assertEqual(3, result.data.resolved)
        self.assertEqual(
            ["START", "END", "LATER-RESOLVED"],
            [detail.key for detail in result.data.created_details],
        )
        self.assertEqual(
            ["OLD-CREATED", "START", "END"],
            [detail.key for detail in result.data.resolved_details],
        )
        self.assertEqual([None, None], self.jira.requested_limits)

    async def test_resolution_statistics_include_end_day_and_exclude_next_day(self) -> None:
        result = await ResolutionCollector(self.jira, self.queries, self.now).collect()

        self.assertEqual(3, result.total)
        self.assertEqual(3, result.data.by_type["인시던트"].count)
        self.assertEqual(3, result.data.by_semester["h2"]["인시던트"].count)
        self.assertEqual(3, result.data.by_status_type["Closed"]["인시던트"].count)
        self.assertEqual([None], self.jira.requested_limits)

    async def test_year_end_details_and_annual_cards_have_identical_counts(self) -> None:
        end_at = datetime.datetime(2026, 12, 31, 23, 59, 59, tzinfo=KST)
        queries = query_builder().build(
            end_at,
            week_start_override=datetime.datetime(2026, 1, 1, tzinfo=KST),
        )
        jira = DateRangeJira([
            issue("PRIOR-YEAR", "2025-12-31T23:59:59", "2025-12-31T23:59:59"),
            issue("YEAR-START", "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
            issue("YEAR-END", "2026-12-31T23:59:59", "2026-12-31T23:59:59"),
            issue("NEXT-YEAR", "2027-01-01T00:00:00", "2027-01-01T00:00:00"),
        ])
        details = await CreatedVsResolvedCollector(jira, queries).collect()
        created = await TypeCountCollector(
            jira, "연간 생성", queries.w1_yearly_created(), list(queries.issue_types),
        ).collect()
        resolved = await TypeCountCollector(
            jira, "연간 해결", queries.w2_yearly_resolved(), list(queries.issue_types),
        ).collect()

        self.assertEqual(2, created.total)
        self.assertEqual(2, resolved.total)
        self.assertEqual(created.total, details.data.created)
        self.assertEqual(resolved.total, details.data.resolved)
        self.assertEqual(["YEAR-START", "YEAR-END"], [row.key for row in details.data.created_details])
        self.assertEqual(["YEAR-START", "YEAR-END"], [row.key for row in details.data.resolved_details])
