# backend/src/presentation/api/deps.py
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.job_runner_port import JobRunnerPort
from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.domain.ports.jira_port import JiraPort
from src.infrastructure.persistence.database import get_db_session


def get_job_runner(request: Request) -> JobRunnerPort:
    return request.app.state.job_runner


def get_jira(request: Request) -> JiraPort:
    return request.app.state.container._jira


async def get_generate_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> GenerateReportUseCase:
    return request.app.state.container.generate_report_use_case(session)


async def get_get_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> GetReportUseCase:
    return request.app.state.container.get_report_use_case(session)
