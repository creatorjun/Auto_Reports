# backend/src/presentation/api/deps.py
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.infrastructure.container import Container
from src.infrastructure.persistence.database import get_db_session


def get_container(request: Request) -> Container:
    return request.app.state.container


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
