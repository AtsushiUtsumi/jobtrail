import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from jobtrail.config import get_settings
from jobtrail.infra.db.models import metadata, start_mappers
from jobtrail.infra.db.session import create_session_factory
from jobtrail.infra.unit_of_work import SqlAlchemyUnitOfWork
from jobtrail.main import create_app
from jobtrail.usecase.context import AppContext

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL が未設定のため DB テストをスキップします")
    return url


@pytest.fixture(scope="session")
def migrated(database_url: str) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")
    start_mappers()


@pytest.fixture
def ctx(database_url: str, migrated: None) -> Iterator[AppContext]:
    session_factory = create_session_factory(database_url)
    assert session_factory.kw["bind"] is not None
    engine = session_factory.kw["bind"]
    with engine.begin() as connection:
        tables = ", ".join(table.name for table in metadata.sorted_tables)
        connection.execute(sa.text(f"TRUNCATE {tables} CASCADE"))
    yield AppContext(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        settings=get_settings(),
    )
    engine.dispose()


@pytest.fixture
def client(ctx: AppContext) -> Iterator[TestClient]:
    with TestClient(create_app(ctx), base_url="http://localhost") as test_client:
        yield test_client
