# backend/tests/test_annual_reports.py
import datetime
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.ports.report_cache_port import ReportCachePort
from src.application.ports.report_repository import ReportRepository
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.refresh_report import RefreshReportUseCase
from src.domain.constants import KST
from src.domain.entities.report import NewReport, Report, ReportScope


class InMemoryReportRepository(ReportRepository):
    def __init__(self, latest: Report | None, annual: Report | None) -> None:
        self.latest = latest
        self.annual = annual
        self.requested_annual_years: list[int] = []
        self.updated: list[Report] = []

    async def save(self, report: NewReport) -> Report:
        raise NotImplementedError

    async def find_by_id(self, report_id: int) -> Report | None:
        return next((report for report in [self.latest, self.annual] if report and report.id == report_id), None)

    async def find_latest(self) -> Report | None:
        return self.latest

    async def find_annual(self, year: int) -> Report | None:
        self.requested_annual_years.append(year)
        return self.annual if self.annual and self.annual.report_year == year else None

    async def find_all(self, limit: int = 20, offset: int = 0) -> list[Report]:
        return []

    async def delete(self, report_id: int) -> bool:
        return False

    async def delete_before(self, cutoff: datetime.date) -> list[int]:
        return []

    async def count_all(self) -> int:
        return 0

    async def update_widgets(self, report_id: int, report: NewReport) -> Report:
        updated = Report(
            id=report_id,
            week_start=report.week_start,
            week_end=report.week_end,
            report_date=report.report_date,
            widgets=report.widgets,
            ai_analysis=report.ai_analysis,
            scope=report.scope,
            report_year=report.report_year,
        )
        self.updated.append(updated)
        return updated


class InMemoryReportCache(ReportCachePort):
    def __init__(self) -> None:
        self.reports: dict[int, Report] = {}
        self.latest_id: int | None = None

    async def get(self, report_id: int, refresh_fn=None) -> Report | None:
        return self.reports.get(report_id)

    async def set(self, report_id: int, report: Report) -> None:
        self.reports[report_id] = report

    async def get_latest_id(self) -> int | None:
        return self.latest_id

    async def set_latest_id(self, report_id: int | None) -> None:
        self.latest_id = report_id

    async def delete(self, report_id: int) -> None:
        self.reports.pop(report_id, None)

    async def aclose(self) -> None:
        self.reports.clear()


class RecordingAssembler:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime.datetime, datetime.datetime | None]] = []

    async def collect(
        self,
        now: datetime.datetime,
        week_start_override: datetime.datetime | None = None,
        annual_report_year: int | None = None,
    ) -> NewReport:
        self.calls.append((now, week_start_override))
        return NewReport(
            week_start=week_start_override.date(),
            week_end=now.date(),
            report_date=now.strftime("%Y-%m-%d %H:%M"),
        )


class FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 1, 12, 0, tzinfo=tz)


class AnnualReportTest(unittest.IsolatedAsyncioTestCase):
    def test_completed_and_current_year_ranges_are_annual(self) -> None:
        now = datetime.datetime(2026, 9, 1, tzinfo=KST)

        completed = GenerateReportUseCase._resolve_scope(
            datetime.datetime(2024, 1, 1, tzinfo=KST),
            datetime.datetime(2024, 12, 31, 23, 59, tzinfo=KST),
            now,
        )
        current = GenerateReportUseCase._resolve_scope(
            datetime.datetime(2026, 1, 1, tzinfo=KST),
            now,
            now,
        )
        weekly = GenerateReportUseCase._resolve_scope(
            datetime.datetime(2026, 8, 26, tzinfo=KST),
            now,
            now,
        )

        self.assertEqual((ReportScope.ANNUAL, 2024), completed)
        self.assertEqual((ReportScope.ANNUAL, 2026), current)
        self.assertEqual((ReportScope.STANDARD, None), weekly)

    async def test_refresh_updates_latest_and_only_the_current_annual_report(self) -> None:
        latest = Report(
            id=1,
            week_start=datetime.date(2026, 8, 25),
            week_end=datetime.date(2026, 8, 31),
            report_date="2026-08-31",
        )
        annual = Report(
            id=2,
            week_start=datetime.date(2026, 1, 1),
            week_end=datetime.date(2026, 8, 31),
            report_date="2026-08-31",
            scope=ReportScope.ANNUAL,
            report_year=2026,
        )
        repository = InMemoryReportRepository(latest, annual)
        cache = InMemoryReportCache()
        assembler = RecordingAssembler()
        use_case = RefreshReportUseCase(assembler, repository, cache)

        with patch("src.application.use_cases.refresh_report.datetime", FixedDateTime):
            await use_case.execute()

        self.assertEqual([2026], repository.requested_annual_years)
        self.assertEqual([1, 2], [report.id for report in repository.updated])
        self.assertEqual(datetime.date(2026, 9, 1), repository.updated[1].week_end)
        self.assertEqual(ReportScope.ANNUAL, repository.updated[1].scope)
        self.assertEqual(1, cache.latest_id)
