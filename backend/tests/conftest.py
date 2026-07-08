# backend/tests/conftest.py
import datetime
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.job import JobRecord, JobStatus
from src.domain.entities.report import NewReport, Report
from src.domain.entities.widget import WidgetResult
from src.domain.ports.ai_port import AiPort
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.report_repository import ReportRepository
from src.domain.value_objects.ai_analysis import AiAnalysis


# ── 공통 픽스체 ────────────────────────────────────────────────

@pytest.fixture
def sample_new_report() -> NewReport:
    return NewReport(
        week_start=datetime.date(2026, 7, 1),
        week_end=datetime.date(2026, 7, 7),
        report_date="2026-07-07 23:00",
        widgets={},
    )


@pytest.fixture
def sample_report(sample_new_report: NewReport) -> Report:
    return Report(
        **{f.name: getattr(sample_new_report, f.name)
           for f in sample_new_report.__dataclass_fields__.values()},
        id=42,
        created_at=datetime.datetime(2026, 7, 7, 23, 0, tzinfo=datetime.timezone.utc),
    )


@pytest.fixture
def good_ai_analysis() -> AiAnalysis:
    return AiAnalysis(
        summary="운영 안정적",
        risks=[],
        recommendations=[],
        sentiment="good",
    )


@pytest.fixture
def mock_ai_port(good_ai_analysis: AiAnalysis) -> AiPort:
    """AiPort 성공 Mock (analyze 항상 good_ai_analysis 반환)"""
    port = AsyncMock(spec=AiPort)
    port.analyze.return_value = good_ai_analysis
    return port


@pytest.fixture
def mock_report_repository(sample_report: Report) -> ReportRepository:
    """ReportRepository Mock"""
    repo = AsyncMock(spec=ReportRepository)
    repo.save.return_value = sample_report
    return repo


@pytest.fixture
def mock_job_repository() -> JobRepository:
    """JobRepository In-Memory Mock"""
    store: dict = {}

    async def _save(record: JobRecord) -> None:
        store[record.job_id] = record

    async def _find(job_id: str) -> Optional[JobRecord]:
        return store.get(job_id)

    repo = AsyncMock(spec=JobRepository)
    repo.save.side_effect = _save
    repo.find.side_effect = _find
    return repo
