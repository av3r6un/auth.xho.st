import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.base import Base

db_url = os.getenv('DB_URL')

engine = create_async_engine(db_url, echo=False, pool_recycle=280, pool_pre_ping=True)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_db():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)


async def drop_db():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)


async def dispose():
  await engine.dispose()
