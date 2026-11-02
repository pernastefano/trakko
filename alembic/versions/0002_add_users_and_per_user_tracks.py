"""Add users and per-user Tracks

Every Track now belongs to a user. Existing data was created before accounts existed and has no
owner, so upgrading deletes it: export it first if you want to keep it.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Single-user data has no owner to assign to: remove it (children first).
    op.execute(sa.text("DELETE FROM entries"))
    op.execute(sa.text("DELETE FROM event_types"))
    op.execute(sa.text("DELETE FROM tracks"))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_index("uq_tracks_single_default", sqlite_where=sa.text("is_default = 1"))
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            "fk_tracks_user_id_users", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_index("ix_tracks_user_id", ["user_id"], unique=False)
        batch_op.create_index(
            "uq_tracks_one_default_per_user",
            ["user_id"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
        )


def downgrade() -> None:
    # Accounts and everything they own are removed; restore the single-user starting point.
    op.execute(sa.text("DELETE FROM entries"))
    op.execute(sa.text("DELETE FROM event_types"))
    op.execute(sa.text("DELETE FROM tracks"))

    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_tracks_one_default_per_user", sqlite_where=sa.text("is_default = 1")
        )
        batch_op.drop_index("ix_tracks_user_id")
        batch_op.drop_constraint("fk_tracks_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.create_index(
            "uq_tracks_single_default",
            ["is_default"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
        )
    op.drop_table("users")
    op.execute(sa.text("INSERT INTO tracks (name, position, is_default) VALUES ('My Track', 0, 1)"))
