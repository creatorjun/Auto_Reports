# backend/src/infrastructure/persistence/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.config.settings import get_settings

_settings = get_settings()
_engine = create_async_engine(
    _settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"ssl": "disable"},
)
AsyncSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
