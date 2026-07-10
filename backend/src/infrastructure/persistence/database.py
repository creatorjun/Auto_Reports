# backend/src/infrastructure/persistence/database.py
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker | None = None


def init_db(database_url: str) -> None:
    global _engine, AsyncSessionLocal
    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args={"ssl": "disable"},
    )
    AsyncSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def close_db() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def get_db_session() -> AsyncSession:
    if AsyncSessionLocal is None:
        raise RuntimeError("DB가 초기화되지 않았습니다. init_db()를 먼저 호출하세요.")
    async with AsyncSessionLocal() as session:
        yield session
