import asyncio
from backend.app.db.session import engine, Base

async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def pytest_sessionstart(session):
    asyncio.run(init_tables())
