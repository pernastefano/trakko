from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import Base, get_session, make_engine, sqlite_url
from app.main import create_app
from app.services import users

PASSWORD = "correct horse battery"

ClientFactory = Callable[..., TestClient]


@pytest.fixture(autouse=True)
def cheap_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hashes carry their own parameters, so tests can use a very cheap scrypt."""
    monkeypatch.setattr(users, "SCRYPT_N", 2**4)


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
    """Build clients on the shared test database; each has its own cookies (signed out)."""

    def make(allow_registration: bool = True, secret_key: str = "test-secret-key") -> TestClient:
        settings = Settings(
            db_path="unused",
            secret_key=secret_key,
            secret_key_is_random=False,
            allow_registration=allow_registration,
        )
        app = create_app()

        def override_session() -> Iterator[Session]:
            with Session(engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    return make


@pytest.fixture
def sign_in(client_factory: ClientFactory, engine: Engine) -> Callable[..., TestClient]:
    """A client signed in as `username`; the account (without any Track) is created if missing."""

    def make(username: str = "alice", **settings: bool | str) -> TestClient:
        client = client_factory(**settings)
        with Session(engine) as session:
            if users.authenticate_or_none(session, username, PASSWORD) is None:
                users.create_user(session, username, PASSWORD, with_default_track=False)
        response = client.post(
            "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return client

    return make


@pytest.fixture
def client(sign_in: Callable[..., TestClient]) -> TestClient:
    """A client signed in as "alice", who starts with no Tracks."""
    return sign_in("alice")
