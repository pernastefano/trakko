from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.db import Base, make_engine, sqlite_url
from app.models import Track

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return sqlite_url(str(tmp_path / "migrated.db"))


@pytest.fixture
def alembic_config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_upgrade_creates_schema_and_default_track(alembic_config: Config, db_url: str) -> None:
    command.upgrade(alembic_config, "head")

    engine = make_engine(db_url)
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
    with Session(engine) as session:
        tracks = session.scalars(select(Track)).all()
    engine.dispose()

    assert len(tracks) == 1
    assert tracks[0].is_default is True


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
