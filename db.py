from __future__ import annotations

from typing import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


# Движок для async SQLite (или другой БД, если поменяешь DATABASE_URL)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,      # можно включить True для отладки SQL
    future=True,
)

# Фабрика асинхронных сессий
async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Удобная обёртка, если хочется писать:
        async with get_session() as session:
            ...
    """
    async with async_session_maker() as session:
        yield session
