"""Bar migration.

Revision ID: bar
Revises: foo
Create Date: 2026-02-17 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bar"
down_revision: str | Sequence[str] | None = "foo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("foo", sa.Column("bar", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("foo", "bar")
