# backend/src/presentation/api/deps.py
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.generate_report import GenerateReportUseCase
from src.application.use_cases.get_report import GetReportUseCase
from src.infrastructure.container import Container
from src.infrastructure.persistence.database import get_db_session

_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    return _container


async def get_generate_use_case(
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_container)
) -> GenerateReportUseCase:
    return container.generate_report_use_case(session)


async def get_get_use_case(
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_container)
) -> GetReportUseCase:
    return container.get_report_use_case(session)
