"""add campaign premise

Revision ID: 8c41f0b2d9a7
Revises: 5d9b1e4a7c20
Create Date: 2026-11-17 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c41f0b2d9a7"
down_revision: str | Sequence[str] | None = "5d9b1e4a7c20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "campaigns",
        sa.Column("premise", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("campaigns", "premise")
