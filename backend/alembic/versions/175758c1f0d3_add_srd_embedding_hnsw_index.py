"""add srd embedding hnsw index

Revision ID: 175758c1f0d3
Revises: fa3cc73579d3
Create Date: 2026-11-16 19:47:29.041308

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "175758c1f0d3"
down_revision: str | Sequence[str] | None = "fa3cc73579d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_srd_chunks_embedding_hnsw",
        "srd_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_srd_chunks_embedding_hnsw",
        table_name="srd_chunks",
    )
