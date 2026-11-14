import asyncio
import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Base(DeclarativeBase):
    """Base class shared by all persisted ORM models."""


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide one database session for each request."""
    async with SessionLocal() as session:
        yield session


async def create_tables_if_needed() -> None:
    """Create application tables without changing existing tables or data."""
    from app import models  # noqa: F401 - imports model metadata before schema creation

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Release database connection-pool resources on application shutdown."""
    await engine.dispose()
