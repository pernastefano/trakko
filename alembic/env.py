from logging.config import fileConfig

from alembic import context
from app import models  # noqa: F401  (registers the models on Base.metadata)
from app.db import Base, configured_url, make_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_url() -> str:
    # An explicit URL (e.g. set by the tests) wins over the environment settings.
    return config.get_main_option("sqlalchemy.url") or configured_url()


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def check_foreign_keys(connection) -> None:
    """Fail loudly if a migration left rows that point at nothing."""
    broken = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if broken:
        raise RuntimeError(f"The migration left broken foreign keys: {broken}")


def run_migrations_online() -> None:
    connectable = make_engine(get_url())

    with connectable.connect() as connection:
        # SQLite changes a table by building a new one and dropping the old one. With foreign keys
        # enforced, dropping a table first deletes its rows, and ON DELETE CASCADE then deletes the
        # rows of every table that refers to it: rebuilding `users` used to wipe every Track, Event
        # Type and Entry. So enforcement stays off while migrating (the pragma is ignored inside a
        # transaction, hence before Alembic starts one) and the result is checked instead.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()
            check_foreign_keys(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
