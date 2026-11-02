from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def sqlite_url(db_path: str) -> str:
    return f"sqlite:///{db_path}"


def configured_url() -> str:
    """URL of the configured database; creates its parent directory if missing."""
    db_path = Path(get_settings().db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite_url(str(db_path))


@lru_cache
def get_engine() -> Engine:
    return make_engine(configured_url())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
