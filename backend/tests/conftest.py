import pytest
import pytest_asyncio
import asyncio
from app.core.config import settings
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

# Create a test engine with NullPool to prevent connection reuse issues between async tests
test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool
)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        # Clean up existing tables for test isolation
        await session.execute(text("TRUNCATE TABLE availability_calendar, assignments, requests, farms, machines, labour_teams, users CASCADE;"))
        await session.commit()
        
        yield session
        
        # Clean up after test
        await session.execute(text("TRUNCATE TABLE availability_calendar, assignments, requests, farms, machines, labour_teams, users CASCADE;"))
        await session.commit()
