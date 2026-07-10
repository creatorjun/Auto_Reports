# backend/src/infrastructure/persistence/database.py
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global _engine, AsyncSessionLocal
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session():
    if AsyncSessionLocal is None:
        raise RuntimeError("DB가 초기화되지 않았습니다.")
    async with AsyncSessionLocal() as session:
        yield session


async def close_db() -> None:
    if _engine is not None:
        await _engine.dispose()
