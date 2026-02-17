"""members initial schema

Revision ID: 20260217_01
Revises:
Create Date: 2026-02-17 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260217_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("members",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ebmember",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "PERSONAL",
                "PROFESSIONAL",
                name="ebclienttype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "social_tariff", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ebproduct",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("ean", sa.Integer(), nullable=False),
        sa.Column(
            "connection_type",
            sa.Enum(
                "ELECTRICITY",
                "GAS",
                name="ebconnectiontype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "grid_operator",
            sa.Enum(
                "IMEWO",
                "WEST",
                "ANTWERPEN",
                "MIDDEN_VLAANDEREN",
                "ZENNE_DIJLE",
                "HALLE_VILVOORDE",
                "KEMPEN",
                "LIMBURG",
                name="gridoperator",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["member_id"], ["ebmember.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ebproduct")
    op.drop_table("ebmember")
