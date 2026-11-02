from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db import Base, make_engine, sqlite_url
from app.models import Track, User

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return sqlite_url(str(tmp_path / "migrated.db"))


@pytest.fixture
def alembic_config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_upgrade_creates_the_schema_without_any_data(alembic_config: Config, db_url: str) -> None:
    command.upgrade(alembic_config, "head")

    engine = make_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    columns = {column["name"] for column in inspect(engine).get_columns("tracks")}
    with Session(engine) as session:
        track_count = session.scalar(select(func.count()).select_from(Track))
        user_count = session.scalar(select(func.count()).select_from(User))
    engine.dispose()

    assert set(Base.metadata.tables) <= tables
    assert "user_id" in columns
    assert (track_count, user_count) == (0, 0)


def test_upgrading_single_user_data_deletes_it(alembic_config: Config, db_url: str) -> None:
    """Data from before accounts has no owner, so migration 0002 removes it."""
    command.upgrade(alembic_config, "0001")
    engine = make_engine(db_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO event_types (track_id, name, color) "
                "SELECT id, 'Running', '#ff0000' FROM tracks"
            )
        )
        connection.execute(
            text(
                "INSERT INTO entries (event_type_id, date, created_at, updated_at) "
                "SELECT id, '2026-11-02', '2026-11-02 00:00:00', '2026-11-02 00:00:00' "
                "FROM event_types"
            )
        )
    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        counts = [
            connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in ("tracks", "event_types", "entries")
        ]
    engine.dispose()

    assert counts == [0, 0, 0]


def test_the_default_track_index_is_per_user(alembic_config: Config, db_url: str) -> None:
    command.upgrade(alembic_config, "head")
    engine = make_engine(db_url)
    with engine.begin() as connection:
        for name in ("alice", "bob"):
            connection.execute(
                text(
                    "INSERT INTO users (username, password_hash, created_at) "
                    f"VALUES ('{name}', 'x', '2026-11-03 00:00:00')"
                )
            )
        for user_id in (1, 2):  # one default Track each is allowed
            connection.execute(
                text(
                    "INSERT INTO tracks (user_id, name, position, is_default) "
                    f"VALUES ({user_id}, 'T', 0, 1)"
                )
            )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text("INSERT INTO tracks (user_id, name, position, is_default) VALUES (1, 'U', 1, 1)")
        )
    engine.dispose()


def test_downgrade_removes_schema(alembic_config: Config, db_url: str) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    engine = make_engine(db_url)
    remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
    engine.dispose()

    assert remaining == set()


def test_models_match_migrations(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")

    # Raises if autogenerate would produce a non-empty migration.
    command.check(alembic_config)


def test_cli_upgrade_creates_missing_database_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    db_file = tmp_path / "missing" / "dir" / "trakko.db"
    monkeypatch.setenv("TRAKKO_DB_PATH", str(db_file))
    get_settings.cache_clear()
    try:
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    finally:
        get_settings.cache_clear()

    assert db_file.exists()


def test_downgrade_restores_the_single_user_starting_point(
    alembic_config: Config, db_url: str
) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "0001")

    engine = make_engine(db_url)
    with engine.connect() as connection:
        tracks = connection.execute(text("SELECT name, is_default FROM tracks")).all()
    engine.dispose()

    assert tracks == [("My Track", 1)]
