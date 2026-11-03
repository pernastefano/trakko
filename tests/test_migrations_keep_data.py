"""Upgrading must never lose what users logged.

SQLite rebuilds a table by dropping it, and with foreign keys on the drop cascades into every table
that refers to it. Migration 0003 rebuilt `users` and wiped all Tracks, Event Types and Entries; the
migration tests of the time only had users, so nothing noticed. These tests migrate real data.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, text

from alembic import command
from app.db import make_engine, sqlite_url

ROOT = Path(__file__).resolve().parent.parent

# Columns that exist in every revision from 0002 on and must come through unchanged.
COLUMNS = {
    "users": "id, username, password_hash, created_at",
    "tracks": "id, user_id, name, position, is_default",
    "event_types": "id, track_id, name, color, icon_kind, icon_value, position",
    "entries": "id, event_type_id, date, note, created_at, updated_at",
}

USERS = 3
TRACKS_PER_USER = 2
TYPES_PER_TRACK = 3
ENTRIES_PER_TYPE = 4


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return sqlite_url(str(tmp_path / "keep.db"))


@pytest.fixture
def alembic_config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


@pytest.fixture
def engine(db_url: str) -> Engine:
    engine = make_engine(db_url)
    yield engine
    engine.dispose()


def seed_accounts_data(engine: Engine) -> None:
    """Fill a database that is at revision 0002 (accounts exist, nothing newer) with real data."""
    with engine.begin() as connection:
        for u in range(1, USERS + 1):
            connection.execute(
                text(
                    "INSERT INTO users (id, username, password_hash, created_at) "
                    "VALUES (:id, :name, :hash, '2026-11-01 08:00:00')"
                ),
                {"id": u, "name": f"user{u}", "hash": f"scrypt$16384$8$1$salt{u}$key{u}"},
            )
            for t in range(TRACKS_PER_USER):
                track_id = (u - 1) * TRACKS_PER_USER + t + 1
                connection.execute(
                    text(
                        "INSERT INTO tracks (id, user_id, name, position, is_default) "
                        "VALUES (:id, :user, :name, :pos, :default)"
                    ),
                    {
                        "id": track_id,
                        "user": u,
                        "name": f"Track {track_id}",
                        "pos": t,
                        "default": int(t == 0),
                    },
                )
                for k in range(TYPES_PER_TRACK):
                    type_id = (track_id - 1) * TYPES_PER_TRACK + k + 1
                    connection.execute(
                        text(
                            "INSERT INTO event_types "
                            "(id, track_id, name, color, icon_kind, icon_value, position) "
                            "VALUES (:id, :track, :name, '#3b82f6', 'emoji', '🏃', :pos)"
                        ),
                        {"id": type_id, "track": track_id, "name": f"Type {type_id}", "pos": k},
                    )
                    for e in range(ENTRIES_PER_TYPE):
                        connection.execute(
                            text(
                                "INSERT INTO entries "
                                "(event_type_id, date, note, created_at, updated_at) "
                                "VALUES (:type, :date, :note, "
                                "'2026-11-02 09:00:00', '2026-11-02 09:00:00')"
                            ),
                            {
                                "type": type_id,
                                "date": f"2026-10-{e + 1:02d}",
                                "note": f"note {type_id}-{e}",
                            },
                        )


def snapshot(engine: Engine) -> dict[str, list[tuple]]:
    with engine.connect() as connection:
        return {
            table: [
                tuple(row)
                for row in connection.execute(text(f"SELECT {columns} FROM {table} ORDER BY id"))
            ]
            for table, columns in COLUMNS.items()
        }


def expected_counts() -> dict[str, int]:
    tracks = USERS * TRACKS_PER_USER
    types = tracks * TYPES_PER_TRACK
    return {
        "users": USERS,
        "tracks": tracks,
        "event_types": types,
        "entries": types * ENTRIES_PER_TYPE,
    }


@pytest.fixture
def seeded(alembic_config: Config, engine: Engine) -> dict[str, list[tuple]]:
    command.upgrade(alembic_config, "0002")
    seed_accounts_data(engine)
    before = snapshot(engine)
    assert {table: len(rows) for table, rows in before.items()} == expected_counts()
    return before


def test_upgrading_to_the_latest_revision_keeps_every_row(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    command.upgrade(alembic_config, "head")

    assert snapshot(engine) == seeded


@pytest.mark.parametrize("revision", ["0003", "0004"])
def test_each_upgrade_step_keeps_every_row(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]], revision: str
) -> None:
    command.upgrade(alembic_config, revision)

    assert snapshot(engine) == seeded


def test_upgrading_one_step_at_a_time_keeps_every_row(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    for revision in ("0003", "0004"):
        command.upgrade(alembic_config, revision)
        assert snapshot(engine) == seeded, f"data changed at {revision}"


def test_downgrading_keeps_every_row(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    command.upgrade(alembic_config, "head")

    command.downgrade(alembic_config, "0002")

    assert snapshot(engine) == seeded


def test_the_new_columns_are_filled_for_existing_users(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT default_view, theme FROM users")).all()

    assert [tuple(row) for row in rows] == [("month", None)] * USERS


def test_foreign_keys_are_consistent_after_migrating(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).fetchall() == []


def test_the_app_enforces_foreign_keys_again_after_migrating(
    alembic_config: Config, engine: Engine, seeded: dict[str, list[tuple]]
) -> None:
    command.upgrade(alembic_config, "head")

    # The migration ran with enforcement off; every normal connection has it on, and cascades work.
    with engine.begin() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        connection.execute(text("DELETE FROM users WHERE id = 1"))
    counts = {table: len(rows) for table, rows in snapshot(engine).items()}
    assert counts["users"] == USERS - 1
    assert counts["tracks"] == (USERS - 1) * TRACKS_PER_USER
    assert counts["entries"] == expected_counts()["entries"] * (USERS - 1) // USERS


def test_the_migration_environment_turns_enforcement_off_and_checks_the_result() -> None:
    environment = (ROOT / "alembic" / "env.py").read_text()

    off = environment.index('exec_driver_sql("PRAGMA foreign_keys=OFF")')
    commit = environment.index("connection.commit()")
    begin = environment.index("context.begin_transaction()", off)
    # Off first, then the implicit transaction is closed, and only then Alembic starts its own.
    assert off < commit < begin
    assert "PRAGMA foreign_key_check" in environment
    assert environment.index("context.run_migrations()", begin) < environment.index(
        "check_foreign_keys(connection)", begin
    )


def test_a_database_with_orphans_is_not_migrated_silently(
    alembic_config: Config, db_url: str
) -> None:
    command.upgrade(alembic_config, "0002")
    engine = make_engine(db_url)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(
            text(
                "INSERT INTO tracks (id, user_id, name, position, is_default) "
                "VALUES (1, 99, 'Orphan', 0, 1)"
            )
        )
    engine.dispose()

    with pytest.raises(RuntimeError, match="broken foreign keys"):
        command.upgrade(alembic_config, "head")
