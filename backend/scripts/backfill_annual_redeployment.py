# backend/scripts/backfill_annual_redeployment.py
import argparse
import asyncio
import dataclasses
import datetime

from src.application.services.query_builder import WidgetQueryBuilder
from src.application.services.query_config import QueryConfig
from src.application.widgets.redeployment_collector import RedeploymentAnalyticsCollector
from src.domain.constants import KST
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.config.settings import get_settings
from src.infrastructure.factories.jira_factory import JiraFactory
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl


async def backfill(years: list[int]) -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    jira = JiraFactory.create(settings)
    queries = WidgetQueryBuilder(
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
            for year in years:
                report = await repository.find_annual(year)
                if report is None:
                    print(f"{year}: annual report not found")
                    continue
                report_end = datetime.datetime(
                    report.week_end.year,
                    report.week_end.month,
                    report.week_end.day,
                    hour=23,
                    minute=59,
                    second=59,
                    tzinfo=KST,
                )
                resolved_queries = queries.build(report_end)
                widget = await RedeploymentAnalyticsCollector(jira, resolved_queries).collect()
                updated = dataclasses.replace(
                    report,
                    widgets={
                        **report.widgets,
                        WidgetId.REDEPLOYMENT_ANALYTICS: widget,
                    },
                )
                await repository.update_widgets(report.id, updated)
                print(f"{year}: report_id={report.id}, redeployment_total={widget.total}")
    finally:
        await jira.aclose()
        await database.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("years", nargs="+", type=int)
    args = parser.parse_args()
    asyncio.run(backfill(args.years))


if __name__ == "__main__":
    main()
