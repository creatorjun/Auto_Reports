# backend/scripts/backfill_unlimited_dashboard_widgets.py
import argparse
import asyncio
import dataclasses
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.count_collector import SimpleWithDetailsCollector
from src.application.widgets.created_vs_resolved_collector import CreatedVsResolvedCollector
from src.domain.constants import KST
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.config.settings import get_settings
from src.infrastructure.factories.jira_factory import JiraFactory
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl


async def backfill(years: list[int], include_latest: bool) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    jira = JiraFactory.create(settings)
    query_builder = WidgetQueryBuilder(
        QueryConfig(
            project_key=settings.project_key,
            issue_types=settings.issue_types,
            active_statuses=settings.active_statuses,
            closed_statuses=settings.closed_statuses,
            sla_threshold_days=settings.sla_threshold_days,
            year_start=settings.year_start,
        )
    )
    try:
        async with database.session() as session:
            repository = ReportRepositoryImpl(session)
            reports = []
            if include_latest:
                latest = await repository.find_latest()
                if latest is not None:
                    reports.append(latest)
            for year in years:
                report = await repository.find_annual(year)
                if report is not None and all(existing.id != report.id for existing in reports):
                    reports.append(report)
            for report in reports:
                report_end = datetime.datetime(
                    report.week_end.year,
                    report.week_end.month,
                    report.week_end.day,
                    hour=23,
                    minute=59,
                    second=59,
                    tzinfo=KST,
                )
                report_start = datetime.datetime(
                    report.week_start.year,
                    report.week_start.month,
                    report.week_start.day,
                    tzinfo=KST,
                )
                queries = query_builder.build(
                    report_end,
                    week_start_override=report_start,
                )
                created_resolved, issue_review = await asyncio.gather(
                    CreatedVsResolvedCollector(jira, queries).collect(),
                    SimpleWithDetailsCollector(
                        jira,
                        "이슈 리뷰 중",
                        queries.w4_issue_review(),
                        max_results=None,
                    ).collect(),
                )
                updated = dataclasses.replace(
                    report,
                    widgets={
                        **report.widgets,
                        WidgetId.CREATED_VS_RESOLVED: created_resolved,
                        WidgetId.ISSUE_REVIEW: issue_review,
                    },
                )
                await repository.update_widgets(report.id, updated)
                print(
                    f"report_id={report.id}, scope={report.scope}, "
                    f"created={created_resolved.data.created}, "
                    f"resolved={created_resolved.data.resolved}, "
                    f"review={issue_review.total}"
                )
    finally:
        await jira.aclose()
        await database.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("years", nargs="*", type=int)
    parser.add_argument("--latest", action="store_true")
    args = parser.parse_args()
    asyncio.run(backfill(args.years, args.latest))


if __name__ == "__main__":
    main()
