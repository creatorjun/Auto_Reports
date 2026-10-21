# backend/src/application/use_cases/trigger_report.py
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import AsyncContextManager
from uuid import uuid4

from src.application.ports.job_runner_port import JobRunnerPort
from src.application.services.report_period import ReportPeriod, report_period_dates
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.constants import KST


class LatestReportUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class TriggerReportResult:
    job_id: str
    start_date: datetime | None
    end_date: datetime | None


class TriggerReportUseCase:
    def __init__(
        self,
        job_runner: JobRunnerPort,
        get_report: Callable[[], AsyncContextManager[GetReportUseCase]],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._job_runner = job_runner
        self._get_report = get_report
        self._clock = clock or (lambda: datetime.now(KST))

    async def execute(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        period: ReportPeriod | None = None,
        selected_date: date | None = None,
        rerun_latest: bool = False,
    ) -> TriggerReportResult:
        if rerun_latest and any(value is not None for value in (period, selected_date, start_date, end_date)):
            raise ValueError("최근 보고서 갱신과 기간 선택을 함께 입력할 수 없습니다.")
        if (period is None) != (selected_date is None):
            raise ValueError("period와 date를 함께 입력해야 합니다.")
        if period is not None and (start_date is not None or end_date is not None):
            raise ValueError("기간 선택과 시작일/종료일을 함께 입력할 수 없습니다.")

        start: datetime | None = None
        end: datetime | None = None
        if rerun_latest:
            async with self._get_report() as reports:
                latest = await reports.get_latest()
            if latest is None:
                raise LatestReportUnavailableError("갱신할 최근 보고서가 없습니다.")
            start = datetime.combine(latest.week_start, time.min, tzinfo=KST)
            end = datetime.combine(latest.week_end, time(23, 59, 59), tzinfo=KST)
        elif period is not None and selected_date is not None:
            start, end = report_period_dates(period, selected_date, self._clock().astimezone(KST).date())
        else:
            if start_date:
                start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=KST)
            if end_date:
                end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=KST)

        job_id = str(uuid4())
        if rerun_latest or period is not None:
            await self._job_runner.submit(job_id, start, end, bypass_jira_cache=True, force_standard=True)
        else:
            await self._job_runner.submit(job_id, start, end, bypass_jira_cache=True)
        return TriggerReportResult(job_id, start, end)
