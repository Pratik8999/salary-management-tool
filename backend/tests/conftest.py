import os
from pathlib import Path

import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://salary:salary@localhost:5432/salary_management_test",
)


def _ensure_test_database_exists(url: str) -> None:
    # Connect to the maintenance `postgres` db and create the target db if missing.
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    target_db = parsed.database
    maintenance_dsn = (
        f"host={parsed.host} port={parsed.port} user={parsed.username} "
        f"password={parsed.password} dbname=postgres"
    )
    with psycopg.connect(maintenance_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{target_db}"')


@pytest.fixture(scope="session")
def test_engine():
    _ensure_test_database_exists(TEST_DATABASE_URL)

    alembic_cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(TEST_DATABASE_URL, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Each test runs inside a transaction that is rolled back at the end."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest_asyncio.fixture
async def client(db_session):
    """An AsyncClient against the FastAPI app, with the DB dependency overridden
    to use the per-test transactional session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# Keep `Base` referenced so static analysers don't flag it; also documents that
# the metadata is what alembic upgrades against.
_ = Base
