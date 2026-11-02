"""Create tracks, event types and entries

Revision ID: 0001
Revises:
Create Date: 2026-11-02 22:55:28.078911

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.create_index(
            "uq_tracks_single_default",
            ["is_default"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
        )

    op.create_table(
        "event_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("icon_kind", sa.String(length=5), server_default="none", nullable=False),
        sa.Column("icon_value", sa.String(length=16), server_default="", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "icon_kind IN ('none', 'emoji', 'text')", name="ck_event_types_icon_kind"
        ),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("event_types", schema=None) as batch_op:
        batch_op.create_index("ix_event_types_track_id", ["track_id"], unique=False)

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("note IS NULL OR length(note) <= 280", name="ck_entries_note_length"),
        sa.ForeignKeyConstraint(["event_type_id"], ["event_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("entries", schema=None) as batch_op:
        batch_op.create_index("ix_entries_date", ["date"], unique=False)
        batch_op.create_index("ix_entries_event_type_id", ["event_type_id"], unique=False)

    # The app needs at least one Track, and exactly one must be the default.
    op.execute(sa.text("INSERT INTO tracks (name, position, is_default) VALUES ('My Track', 0, 1)"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("entries", schema=None) as batch_op:
        batch_op.drop_index("ix_entries_event_type_id")
        batch_op.drop_index("ix_entries_date")

    op.drop_table("entries")
    with op.batch_alter_table("event_types", schema=None) as batch_op:
        batch_op.drop_index("ix_event_types_track_id")

    op.drop_table("event_types")
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_index("uq_tracks_single_default", sqlite_where=sa.text("is_default = 1"))

    op.drop_table("tracks")
