"""Add the color theme to users

The theme moves from a per-device choice to the account. The column is NULL until a theme is chosen,
so the first device of an existing user can hand its current theme over to the account.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("theme", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("theme")
