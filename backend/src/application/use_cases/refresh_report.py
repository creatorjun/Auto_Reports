# backend/src/application/use_cases/refresh_report.py
import logging
from datetime import datetime
from typing import Optional

from src.application.ports.report_cache_port import ReportCachePort
from src.application.services.report_assembler import ReportAssembler
from src.application.use_cases.notify_todo_issues import NotifyTodoIssuesUseCase, _TODO_STATUSES
from src.domain.entities.widget_data import RecentIssueWidgetData
from src.domain.repositories.report_repository import ReportRepository
from src.shared.constants import KST

logger = logging.getLogger(__name__)


class RefreshReportUseCase:
    def __init__(
        self,
        assembler: ReportAssembler,
        repository: ReportRepository,
        cache: ReportCachePort,
        notify: Optional[NotifyTodoIssuesUseCase] = None,
    ):
        self._assembler = assembler
        self._repository = repository
        self._cache = cache
        self._notify = notify

    async def execute(self) -> None:
        latest = await self._repository.find_latest()
        if latest is None:
            logger.info("[RefreshReport] \uc800\uc7a5\ub41c \ubcf4\uace0\uc11c \uc5c6\uc74c \u2014 \uac31\uc2e0 \uc0dd\ub7b5")
            return

        now = datetime.now(tz=KST)
        week_start = datetime(
            latest.week_start.year,
            latest.week_start.month,
            latest.week_start.day,
            tzinfo=KST,
        )
        week_end = datetime(
            latest.week_end.year,
            latest.week_end.month,
            latest.week_end.day,
            tzinfo=KST,
        )

        new_report = await self._assembler.collect(
            now=week_end,
            week_start_override=week_start,
        )

        updated = await self._repository.update_widgets(latest.id, new_report)
        await self._cache.set(updated.id, updated)
        await self._cache.set_latest_id(updated.id)
        logger.info(f"[RefreshReport] \ubcf4\uace0\uc11c ID={updated.id} \uac31\uc2e0 \uc644\ub8cc ({now.strftime('%H:%M:%S')})")

        if self._notify is None:
            return

        todo_issues = self._extract_todo_issues(new_report.widgets)
        if todo_issues:
            try:
                await self._notify.execute(todo_issues)
            except Exception as exc:
                logger.error(f"[RefreshReport] \uba54\uc77c \ubc1c\uc1a1 \uc2e4\ud328: {exc}")

    @staticmethod
    def _extract_todo_issues(widgets: dict) -> list[dict]:
        from src.domain.value_objects.widget_id import WidgetId
        recent_result = widgets.get(WidgetId.RECENT)
        if recent_result is None:
            return []
        data = recent_result.data
        if not isinstance(data, RecentIssueWidgetData):
            return []
        todo = [
            {
                "key": detail.key,
                "fields": {
                    "summary": detail.summary,
                    "issuetype": {"name": detail.type},
                    "created": detail.created,
                    "status": {"name": detail.status},
                },
            }
            for detail in data.issue_details
            if detail.status in _TODO_STATUSES
        ]
        return todo
