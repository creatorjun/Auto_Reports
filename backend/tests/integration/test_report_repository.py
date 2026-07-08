# backend/tests/integration/test_report_repository.py
"""
ReportRepositoryImpl 실DB 통합 테스트.

실행하려면 testcontainers-python을 설치하고
`pytest tests/integration/ -v` 로 실행하세요.

    pip install testcontainers[postgres] asyncpg sqlalchemy pytest-asyncio

이 파일은 실제 DB를 마운트하지 않으면 테스트가 자동으로 skip됩니다.
"""
import datetime
import os

import pytest

pytest.importorskip("testcontainers", reason="testcontainers not installed — skip integration tests")

from testcontainers.postgres import PostgresContainer  # noqa: E402


@pytest.fixture(scope="module")
def postgres_url():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_save_and_find_by_id(postgres_url, sample_new_report):
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from src.infrastructure.persistence.database import Base
    from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl

    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        repo = ReportRepositoryImpl(session)
        saved = await repo.save(sample_new_report)
        assert saved.id > 0
        found = await repo.find_by_id(saved.id)
        assert found is not None
        assert found.report_date == sample_new_report.report_date
