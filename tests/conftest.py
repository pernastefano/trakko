from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import Base, get_session, make_engine, sqlite_url
from app.main import create_app

ClientFactory = Callable[..., TestClient]


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(sqlite_url(str(tmp_path / "test.db")))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client_factory(engine: Engine) -> ClientFactory:
    def make(password: str | None = None, secret_key: str | None = None) -> TestClient:
        settings = Settings(db_path="unused", password=password, secret_key=secret_key)
        app = create_app()

        def override_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    return make


@pytest.fixture
def client(client_factory: ClientFactory) -> TestClient:
    return client_factory()
