"""Add the default calendar view to users

Each user can choose the calendar view the app opens with: day, week or month (the default).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("default_view", sa.String(length=5), server_default="month", nullable=False)
        )
        batch_op.create_check_constraint(
            "ck_users_default_view", "default_view IN ('day', 'week', 'month')"
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("ck_users_default_view", type_="check")
        batch_op.drop_column("default_view")
