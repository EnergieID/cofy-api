"""members core initial schema

Revision ID: members_core_0001
Revises:
Create Date: 2026-02-17 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "members_core_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("members_core",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "member",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("activation_code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activation_code"),
    )
    op.create_index(
        "ix_member_activation_code",
        "member",
        ["activation_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_members_activation_code", table_name="members")
    op.drop_table("members")
