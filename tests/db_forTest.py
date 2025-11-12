"""
Make a test SQLITE database, that's refreshed every use.
"""
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)

from main_tool.core.database.db_test import Base, User, UserConfig

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_tmp.db"

engine_test = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
testing_session_local = async_sessionmaker(engine_test, expire_on_commit=False)

async def create_db_and_tables():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with testing_session_local() as session:
        yield session

async def get_user_db_override():
    async for session in get_async_session():
        yield SQLAlchemyUserDatabase(session, User)
