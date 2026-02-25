"""Make members email and activation_code optional

Revision ID: 537edd2211fa
Revises: members_core_0001
Create Date: 2026-02-25 09:40:46.419081

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "537edd2211fa"
down_revision: str | Sequence[str] | None = "members_core_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("member") as batch_op:
        batch_op.alter_column("email", existing_type=sa.VARCHAR(), nullable=True)
        batch_op.alter_column("activation_code", existing_type=sa.VARCHAR(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("member") as batch_op:
        batch_op.alter_column("activation_code", existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column("email", existing_type=sa.VARCHAR(), nullable=False)
