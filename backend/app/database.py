"""SQLAlchemy async engine and session management.

Uses SQLite for local development (aiosqlite).
Switch to PostgreSQL for production by changing DATABASE_URL:

    postgresql+asyncpg://user:pass@host/dbname
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    from app.models import user, order, points_ledger  # noqa: F401 — ensure models loaded

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (url=%s)", settings.database_url)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: provide an async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
