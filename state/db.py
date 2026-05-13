from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def normalize_database_url(database_url: str) -> str:
    """Normalize provider URLs to SQLAlchemy asyncpg URLs.

    Render commonly injects `postgres://...` or `postgresql://...`.
    This app uses `create_async_engine`, so enforce `postgresql+asyncpg://...`.
    """
    normalized = database_url
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)
    if normalized.startswith("postgresql://") and "postgresql+asyncpg://" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
    return normalized


DATABASE_URL = normalize_database_url(os.environ["DATABASE_URL"])

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
