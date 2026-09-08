import os
from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set testing environment before any app imports
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REQUIRE_EXPLICIT_APPROVAL"] = "True"

from app.config.settings import Settings, get_settings
from app.database.session import get_db
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session")
def test_settings(tmp_path_factory) -> Settings:
    temp_storage = tmp_path_factory.mktemp("test_storage")
    settings = Settings(
        app_name="Job Application Agent (Test)",
        app_env="testing",
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        storage_dir=temp_storage,
        resumes_dir=temp_storage / "resumes",
        sessions_dir=temp_storage / "sessions",
        screenshots_dir=temp_storage / "screenshots",
        require_explicit_approval=True,
    )
    settings.ensure_directories_exist()
    return settings


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    # Override get_db dependency to use the function-scoped in-memory session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    def override_get_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()
